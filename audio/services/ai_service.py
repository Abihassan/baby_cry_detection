import torch
import librosa
from transformers import (
    pipeline,
    AutoFeatureExtractor,
    AutoModelForAudioClassification,
    AutoTokenizer,
    AutoModelForCausalLM
)

class AIService:
    def __init__(self):
        """Pre-loads all models into memory to ensure offline inference."""
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

        # 1. STT: Whisper Tiny
        self.stt_pipe = pipeline(
            "automatic-speech-recognition", 
            model="openai/whisper-tiny", 
            device=self.device
        )
        
        # 2. Sound Detection: AST AudioSet
        self.ast_extractor = AutoFeatureExtractor.from_pretrained("MIT/ast-finetuned-audioset-10-10-0.4593")
        self.ast_model = AutoModelForAudioClassification.from_pretrained(
            "MIT/ast-finetuned-audioset-10-10-0.4593"
        ).to(self.device)
        
        # 3. Contextual LLM: Qwen2.5 0.5B Instruct
        self.llm_tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-0.5B-Instruct")
        self.llm_model = AutoModelForCausalLM.from_pretrained(
            "Qwen/Qwen2.5-0.5B-Instruct", 
            torch_dtype=self.torch_dtype,
            low_cpu_mem_usage=True,
            device_map="auto" if torch.cuda.is_available() else None
        )
        
        if not torch.cuda.is_available():
            self.llm_model = self.llm_model.to(self.device)

    def transcribe(self, file_path: str) -> str:
        """Extracts spoken text from the audio track."""
        try:
            result = self.stt_pipe(
                file_path,
                return_timestamps=True,
                chunk_length_s=30,
                generate_kwargs={"no_repeat_ngram_size": 3}
            )
            return result.get("text", "").strip()
        except Exception:
            return ""

    def detect_sounds(self, file_path: str) -> list:
        """Identifies environmental noises using the Audio Spectrogram Transformer."""
        try:
            audio, sr = librosa.load(file_path, sr=16000, mono=True)
            inputs = self.ast_extractor(audio, sampling_rate=16000, return_tensors="pt").to(self.device)
            
            with torch.no_grad():
                outputs = self.ast_model(**inputs)
                
            logits = outputs.logits
            probs = torch.nn.functional.softmax(logits, dim=-1)
            top_probs, top_indices = torch.topk(probs, 5)
            
            results = []
            for p, idx in zip(top_probs.squeeze().tolist(), top_indices.squeeze().tolist()):
                if p > 0.03:  
                    label = self.ast_model.config.id2label[idx]
                    results.append({"sound": label, "confidence": round(p, 3)})
            return results
        except Exception as e:
            print(f"Sound detection error: {e}")
            return []

    def analyze_context(self, raw_transcription: str, sounds: list) -> tuple[str, str, bool]:
        """Inverted Architecture: Python handles the rules, LLM generates a concise summary."""
        
        # 1. Acoustic Speech Gating
        speech_keywords = ["speech", "conversation", "narration", "monologue", "whispering", "babbling", "vocal"]
        has_real_speech = any(any(kw in s["sound"].lower() for kw in speech_keywords) for s in sounds)
        
        final_transcription = raw_transcription if has_real_speech and raw_transcription else "[No Human Speech Detected]"
        
        # 2. Deterministic Alert Logic (Python Rules Engine)
        critical_keywords = ["baby cry", "infant cry", "crying", "sobbing", "scream", "shout", "glass", "break"]
        has_distress = any(any(kw in s["sound"].lower() for kw in critical_keywords) for s in sounds)
        
        is_alert = has_distress
        
        # 3. LLM Explanation Engine (Polished for the 0.5B Model)
        sound_desc = ", ".join([f"{s['sound']} ({int(s['confidence']*100)}%)" for s in sounds]) if sounds else "None detected"
        
        # We give the LLM aggressive boundaries so it doesn't ramble
        system_prompt = (
            "You are a direct, concise Smart Baby Monitor AI. "
            f"The alarm status is ALREADY SET TO: {'TRIGGERED' if is_alert else 'SAFE'}. "
            "Explain why in exactly one short sentence using the detected sounds. "
            "Do NOT use phrases like 'Based on the audio', 'The system', or 'Without human speech'. Just state the facts."
        )
        
        user_prompt = f"Sounds: {sound_desc}\nExplanation:"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        text = self.llm_tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.llm_tokenizer([text], return_tensors="pt").to(self.device)
        
        with torch.no_grad():
            outputs = self.llm_model.generate(
                **inputs, 
                max_new_tokens=100,  # Increased to prevent mid-sentence cutoffs
                do_sample=False,
                repetition_penalty=1.2
            )
            
        generated_ids = [output_ids[len(input_ids):] for input_ids, output_ids in zip(inputs.input_ids, outputs)]
        explanation = self.llm_tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0].strip()
        
        return final_transcription, f"Reasoning: {explanation}", is_alert

# Singleton assignment
_ai_service_instance = None

def get_ai_service() -> AIService:
    global _ai_service_instance
    if _ai_service_instance is None:
        _ai_service_instance = AIService()
    return _ai_service_instance