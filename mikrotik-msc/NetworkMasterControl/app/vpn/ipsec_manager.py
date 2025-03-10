import subprocess

def configure_ipsec(vpn_config):
    try:
        subprocess.run(["ipsec", "restart"], check=True)
        subprocess.run(["ipsec", "up", vpn_config], check=True)
        print("IPsec VPN configured successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to configure IPsec VPN: {e}")

# Example usage
if __name__ == "__main__":
    configure_ipsec("vpn_config_name")
