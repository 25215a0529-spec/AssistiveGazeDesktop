import threading
import subprocess
import sys

class SpeechEngine:
    def __init__(self):
        pass

    def build_sov_sentence(self, category: str, object_item: str) -> str:
        # Category: खाना
        if category == "खाना":
            if object_item in ["दाल रोटी", "चावल सब्ज़ी", "दाल भात", "चावल"]:
                return f"मुझे खाने में {object_item} चाहिए"
            elif object_item in ["नाश्ता", "टिफ़िन"]:
                return f"मुझे {object_item} चाहिए"
            elif object_item in ["बिस्कुट", "बस्कुट"]:
                return "मुझे बिस्कुट चाहिए"
            elif object_item == "कुछ और":
                return "मुझे खाने में कुछ और चाहिए"
            return f"मुझे खाने में {object_item} चाहिए"

        # Category: जाना है
        elif category == "जाना है":
            if object_item in ["घर", "कमरे में", "बाहर", "अस्पताल", "वॉशरूम", "बिस्तर पर", "बगीचे में"]:
                return f"मुझे {object_item} जाना है"
            return "मुझे जाना है"

        # Category: दर्द
        elif category == "दर्द":
            if object_item in ["कहीं", "दर्द"]:
                return "मुझे दर्द हो रहा है"
            return f"मुझे {object_item} दर्द हो रहा है"

        # Direct root triggers (Cleaned to prevent duplicate phrases)
        elif category == "पानी":
            return "मुझे पानी चाहिए"
        elif category == "मदद":
            return "मुझे मदद चाहिए"

        return f"{object_item}"

    def speak(self, text: str):
        def _speak():
            try:
                import pythoncom
                import pyttsx3
                pythoncom.CoInitialize()
                engine = pyttsx3.init()
                engine.setProperty("rate", 125)
                engine.say(text)
                engine.runAndWait()
                engine.stop()
                pythoncom.CoUninitialize()
                return
            except Exception as e:
                print(f"[TTS Fallback Triggered]: {e}")

            if sys.platform == "win32":
                try:
                    clean_text = text.replace('"', '').replace("'", "")
                    cmd = f'powershell -Command "Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak(\'{clean_text}\')"'
                    subprocess.run(cmd, shell=True, capture_output=True)
                except Exception as err:
                    print(f"[TTS SAPI Failed]: {err}")

        threading.Thread(target=_speak, daemon=True).start()