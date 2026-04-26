import socket
import struct
import torch
import numpy as np
import subprocess
import time
import sys
from faster_whisper import WhisperModel
from ollama import Client

# ==========================================
# SYSTEM CONFIGURATION
# ==========================================
# Network settings for G1 audio loop
GROUP_IP = "239.168.123.161"
PORT = 5555
LOCAL_IP = "192.168.123.164" 
SAMPLE_RATE = 16000

# YOUR GPU WORKSTATION CONFIG (Updated from 'ip a' output)
WORKSTATION_IP = "192.168.0.91" 
OLLAMA_ENDPOINT = f"http://{WORKSTATION_IP}:11434"

# PATHS (Absolute path for the TTS binary)
TTS_BINARY_PATH = "/home/unitree/Documents/G1_Projs/unitree_sdk2/build/bin/g1_tts_test"

print("🎙️ Initializing Silero VAD (Local G1)...")
model_vad, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad', model='silero_vad')

print("🧠 Loading Faster-Whisper (Local G1)...")
stt_model = WhisperModel("base", device="cpu", compute_type="int8")

print(f"🔗 Connecting to external Brain at {OLLAMA_ENDPOINT}...")
ollama_client = Client(host=OLLAMA_ENDPOINT)

# ==========================================
# SUPPORT FUNCTIONS
# ==========================================

def request_image_from_cpp():
    """Pings the local C++ server on G1 to get a camera frame."""
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.settimeout(2.0)
        client_socket.connect(('127.0.0.1', 8080))
        
        image_data = []
        while True:
            chunk = client_socket.recv(4096)
            if not chunk: break
            image_data.append(chunk.decode('utf-8'))
            
        client_socket.close()
        full_base64 = "".join(image_data)
        return full_base64 if (full_base64 != "ERROR" and full_base64 != "") else None
    except Exception as e:
        print(f"❌ Camera Server Error: {e}")
        return None

def speak_with_c(text):
    """Executes the G1's local TTS binary using absolute path."""
    if not text.strip(): return
    try:
        # Clean text for shell execution
        clean_text = text.replace('"', '').replace("'", "")
        subprocess.run([TTS_BINARY_PATH, clean_text], check=True)
        
        # Dynamic pause based on word count
        word_count = len(text.split())
        time.sleep((word_count / 2.5) + 0.5)
    except Exception as e:
        print(f"❌ TTS Error: {e}")

def record_with_vad():
    """Listens to G1 microphone and detects end of speech."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', PORT))
    mreq = struct.pack("4s4s", socket.inet_aton(GROUP_IP), socket.inet_aton(LOCAL_IP))
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    pcm_data = bytearray()
    speaking_started = False
    silence_counter = 0

    print("\n👂 Listening... (Speak to the G1)")
    try:
        while True:
            data, _ = sock.recvfrom(2048) 
            pcm_data.extend(data)
            audio_int16 = np.frombuffer(data, dtype=np.int16)
            audio_float32 = audio_int16.astype(np.float32) / 32768.0
            confidence = model_vad(torch.from_numpy(audio_float32), SAMPLE_RATE).item()

            if confidence > 0.5:
                if not speaking_started: print("🎤 Voice detected!")
                speaking_started = True
                silence_counter = 0
            elif speaking_started:
                silence_counter += 1
            
            if speaking_started and silence_counter > 25:
                print("✅ End of speech detected.")
                break
        return pcm_data
    finally:
        sock.close()

def transcribe_fast(audio_bytes):
    """Converts recorded audio to text locally on the G1."""
    audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
    segments, _ = stt_model.transcribe(audio_np, beam_size=1, language="en")
    return "".join([s.text for s in segments]).strip()

# ==========================================
# MAIN OPERATIONAL LOOP
# ==========================================
if __name__ == "__main__":
    print("\n🤖 G1 MAESTRO: BASELINE AGENT ACTIVE")
    
    while True:
        try:
            line = input("👉 How many sentences max per response? (default 2): ")
            MAX_SENTENCES = int(line) if line.strip() else 2
            break
        except: print("Invalid number. Please enter an integer.")

    system_prompt = f"You are a Unitree G1 robot conductor. You can see through your camera. Reply concisely in exactly {MAX_SENTENCES} sentences max."

    while True:
        try:
            # 1. Perception: Listen
            audio = record_with_vad()
            if len(audio) < 8000: continue

            # 2. Perception: Transcribe
            print("🧠 Analyzing voice...")
            user_msg = transcribe_fast(audio)
            if not user_msg: continue
            print(f"👤 User: {user_msg}")

            # 3. Perception: Capture Image from C++ Server
            base64_img = request_image_from_cpp()

            # 4. Thinking: Offload Inference to Workstation
            print(f"🚀 Sending to Workstation ({WORKSTATION_IP})...")
            payload = {'role': 'user', 'content': user_msg}
            if base64_img:
                payload['images'] = [base64_img]

            response_stream = ollama_client.chat(
                model='qwen2.5vl:7b', # Updated tag
                messages=[{'role': 'system', 'content': system_prompt}, payload],
                stream=True
            )
            
            # 5. Action: Stream and Speak
            print("🤖 G1: ", end="", flush=True)
            current_sentence = ""
            sentence_count = 0
            
            for chunk in response_stream:
                word = chunk['message']['content']
                print(word, end="", flush=True)
                current_sentence += word
                
                if any(p in word for p in ['.', '!', '?']):
                    if len(current_sentence.strip()) > 3:
                        speak_with_c(current_sentence.strip())
                        current_sentence = ""
                        sentence_count += 1
                        if sentence_count >= MAX_SENTENCES: break
            
            if current_sentence.strip() and sentence_count < MAX_SENTENCES:
                speak_with_c(current_sentence.strip())
            
            print("\n")

        except KeyboardInterrupt:
            print("\n👋 System shut down.")
            break
        except Exception as e:
            print(f"\n⚠️ Runtime Error: {e}")
            time.sleep(2)
