try:
    import ingest
    print("Ingest imported successfully")
except Exception as e:
    print(f"Error importing ingest: {e}")
    import traceback
    traceback.print_exc()
