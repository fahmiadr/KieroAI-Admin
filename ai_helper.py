import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('GEMINI_API_KEY')

def analyze_log_content(log_text, service_name, service_type="backend"):
    """
    Fungsi: Mengirim log ke AI dan meminta solusi perbaikan.
    Args:
        log_text (str): Potongan log error.
        service_name (str): Nama layanan (misal: 'Kawalo API').
        service_type (str): 'backend' atau 'frontend'.
    """
    if not API_KEY:
        return "<div class='alert-custom' style='background: rgba(255, 159, 10, 0.15); border: 1px solid rgba(255, 159, 10, 0.3);'><i class='bi bi-exclamation-triangle-fill' style='color: #FF9F0A;'></i> <span>API Key tidak ditemukan. Tambahkan GEMINI_API_KEY di file .env</span></div>"

    try:
        genai.configure(api_key=API_KEY)
        # Use gemini-2.0-flash or fallback to gemini-pro if needed
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Prompt Engineering: Instruksi agar AI paham konteks
        role_desc = "Full Stack Engineer" if service_type == "frontend" else "DevOps & Backend Engineer"
        
        prompt = f"""
        Bertindaklah sebagai Senior {role_desc}.
        Analisa log error berikut dari layanan '{service_name}' (Tipe: {service_type}).
        
        Berikan respon dalam format HTML (tanpa tag ```html, hanya isinya saja).
        Gunakan Bahasa Indonesia.
        Gunakan style inline yang cocok dengan dark theme (background gelap, teks terang).
        
        Struktur Jawaban:
        <div style="background: rgba(255, 69, 58, 0.15); border: 1px solid rgba(255, 69, 58, 0.3); border-radius: 10px; padding: 14px; margin-bottom: 16px;">
            <strong style="color: #FF453A;">❌ Ringkasan Masalah:</strong>
            <span style="color: #e0e0e0;"> [Jelaskan error dalam 1 kalimat]</span>
        </div>
        
        <h4 style="color: #0A84FF; margin-bottom: 12px;">🔍 Analisa Akar Masalah</h4>
        <p style="color: #ccc; line-height: 1.6;">[Penjelasan teknis kenapa error ini terjadi]</p>
        
        <h4 style="color: #30D158; margin-bottom: 12px;">🛠️ Solusi Perbaikan</h4>
        <ol style="color: #e0e0e0; line-height: 1.8;">
            <li>[Langkah konkrit 1]</li>
            <li>[Langkah konkrit 2 - sertakan command terminal jika perlu dalam <code style="background: rgba(255,255,255,0.1); padding: 2px 6px; border-radius: 4px;">code tags</code>]</li>
        </ol>

        Log Content:
        {log_text}
        """

        response = model.generate_content(prompt)
        return response.text

    except Exception as e:
        return f"<div class='alert-custom' style='background: rgba(255, 69, 58, 0.15); border: 1px solid rgba(255, 69, 58, 0.3);'><i class='bi bi-x-circle-fill' style='color: #FF453A;'></i> <span>Gagal koneksi ke AI: {str(e)}</span></div>"
