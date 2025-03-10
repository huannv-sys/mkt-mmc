import yaml

def load_config(file_path):
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)

# Example usage
if __name__ == "__main__":
    config = load_config('config/settings.yaml')
    print(config)
