import uuid
from custom_components.inim_cloud.api import InimCloudAPI


def main():
    client_id = f"home-{str(uuid.uuid4()).upper()}"
    api = InimCloudAPI(client_id)
    username = "username"
    password = "password"
    auth_data = api.authenticate(username, password)
    # print(auth_data)

    devices = api.get_devices()
    print(f"Devices: {devices}")

    s = api.activate_scenario("545002", "1")
    print(f"Activate scenario: {s}")


if __name__ == "__main__":
    main()
