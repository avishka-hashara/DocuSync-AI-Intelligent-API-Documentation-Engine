import ast

def extract_code_chunks(filepath):
    # Read the raw source code
    with open(filepath, 'r', encoding='utf-8') as file:
        source_code = file.read()

    # Parse the code into an Abstract Syntax Tree
    tree = ast.parse(source_code)
    chunks = []

    # Loop through the top-level structures in the file
    for node in tree.body:
        # We only care about Functions and Classes for our documentation
        if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
            
            # Extract the exact string of code for this specific function/class
            chunk_code = ast.get_source_segment(source_code, node)
            
            # Determine if it's a Class or Function
            node_type = "Function" if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) else "Class"
            
            chunks.append({
                "name": node.name,
                "type": node_type,
                "code": chunk_code,
                "filepath": filepath
            })
    
    return chunks

if __name__ == "__main__":
    print("Testing AST Parser...")
    
    # Let's test the parser by having it parse ITSELF!
    test_file = __file__
    
    try:
        chunks = extract_code_chunks(test_file)
        print(f"Success! Found {len(chunks)} chunk(s) in {test_file}\n")
        
        for chunk in chunks:
            print(f"--- {chunk['type']}: {chunk['name']} ---")
            # Print the first 100 characters to verify it grabbed the code
            print(f"{chunk['code'][:100]}...\n")
            
    except Exception as e:
        print(f"Error parsing file: {e}")