try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    print("Import ChatGoogleGenerativeAI successful")
except Exception as e:
    print(f"Import ChatGoogleGenerativeAI failed: {e}")
