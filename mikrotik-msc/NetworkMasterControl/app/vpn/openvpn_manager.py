import subprocess

def configure_openvpn(vpn_config):
    try:
        subprocess.run(["openvpn", "--config", vpn_config], check=True)
        print("OpenVPN configured successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to configure OpenVPN: {e}")

# Example usage
if __name__ == "__main__":
    configure_openvpn("/etc/openvpn/vpn_config.ovpn")
