from mikrotik_api import MikroTikAPI

class CAPsMANAPI(MikroTikAPI):
    def provision_ap(self, ap_mac, ap_name):
        data = {
            "mac-address": ap_mac,
            "name": ap_name,
        }
        return self.post_request("caps-man/remote-cap/add", data)

# Example usage
if __name__ == "__main__":
    capsman_api = CAPsMANAPI(base_url="http://192.168.88.1", username="admin", password="password")
    print(capsman_api.provision_ap("00:00:00:00:00:01", "AP1"))
