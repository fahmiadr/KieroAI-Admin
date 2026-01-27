try:
    import google.generativeai as genai
    print("SUCCESS: google.generativeai imported")
    
    from ai_helper import analyze_log_content
    print("SUCCESS: ai_helper imported")
    
except Exception as e:
    print(f"ERROR: {e}")
