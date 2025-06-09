import os

def create_env_file():
    print("Foursquare API Key Setup")
    print("-----------------------")
    
    # Get API key from user
    api_key = input("Please enter your Foursquare API key: ").strip()
    
    if not api_key:
        print("Error: API key cannot be empty!")
        return
    
    # Create .env file content
    env_content = f"FOURSQUARE_API_KEY={api_key}"
    
    # Write to .env file
    try:
        with open('.env', 'w') as f:
            f.write(env_content)
        print("\n.env file created successfully!")
        print("Location:", os.path.abspath('.env'))
    except Exception as e:
        print(f"\nError creating .env file: {e}")

if __name__ == "__main__":
    create_env_file() 