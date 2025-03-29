import socket
import json
import threading
from queue import Queue


def client_mobile():
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(("127.0.0.1", 5555))

    logged_in = False
    selected_car = None
    response_queue = Queue()
    running = True

    def receiver():
        while running:
            try:
                data = client.recv(4096)
                if not data:
                    break

                buffer = data.decode("utf-8")
                while buffer:
                    try:
                        msg, offset = json.JSONDecoder().raw_decode(buffer)
                        buffer = buffer[offset:].lstrip()

                        if msg.get("type") == "notification":
                            print(f"\n[NOTIFICATION] {msg['message']}")
                        else:
                            response_queue.put(msg)

                    except json.JSONDecodeError:
                        break

            except Exception as e:
                print(f"\nConnection error: {e}")
                break

    threading.Thread(target=receiver, daemon=True).start()

    while running:
        try:
            if not logged_in:
                action = input("\nAction (register/login/exit): ").lower()
                if action == "exit":
                    running = False
                    break

                req = {"action": action}
                if action in ["register", "login"]:
                    req["username"] = input("Username: ")
                    req["password"] = input("Password: ")
                    if action == "register":
                        req["license"] = input("License: ")

                client.send(json.dumps(req).encode("utf-8"))
                response = response_queue.get(timeout=5)

                print(f"Response: {response.get('message')}")
                if response.get("message") == "Login successful":
                    logged_in = True

            else:
                action = input(
                    "\nAction (query_cars/select_car/start_rental/drive/end_rental/pay_statistics/logout/exit): ").lower()
                if action == "exit":
                    running = False
                    break

                req = {"action": action}

                # Handle logout separately
                if action == "logout":
                    client.send(json.dumps(req).encode("utf-8"))
                    response = response_queue.get(timeout=5)
                    print(f"Response: {response.get('message')}")
                    if response.get("message") == "Logout successful":
                        logged_in = False
                        selected_car = None
                        continue  # Revine la meniul principal

                # Handle end_rental with payment flow
                elif action == "end_rental":
                    client.send(json.dumps(req).encode("utf-8"))
                    response = response_queue.get(timeout=5)
                    print(f"Response: {response.get('message')}")

                    if response.get("message") == "Proceed to payment":
                        while True:
                            pay_action = input("Enter 'pay_statistics' to complete payment: ").lower()
                            if pay_action == "pay_statistics":
                                client.send(json.dumps({"action": "pay_statistics"}).encode("utf-8"))
                                pay_response = response_queue.get(timeout=5)
                                print(f"Payment: {pay_response.get('message')}")
                                if pay_response.get("message") == "Payment completed":
                                    break  # Ieșim din loop-ul de plată
                            else:
                                print("Invalid option! Payment is mandatory")

                # Handle car selection
                elif action == "select_car":
                    req["car_id"] = input("Car ID: ")
                    client.send(json.dumps(req).encode("utf-8"))
                    response = response_queue.get(timeout=5)
                    print(f"Response: {response.get('message')}")
                    if "selected" in response.get("message", ""):
                        selected_car = req["car_id"]

                # Handle start rental
                elif action == "start_rental":
                    if not selected_car:
                        print("Error: You must select a car first!")
                        continue
                    req["car_id"] = selected_car
                    client.send(json.dumps(req).encode("utf-8"))
                    response = response_queue.get(timeout=5)
                    print(f"Response: {response.get('message')}")

                # Handle query cars
                elif action == "query_cars":
                    client.send(json.dumps(req).encode("utf-8"))
                    response = response_queue.get(timeout=5)
                    if response.get("message") == "No cars available":  # Afișează mesajul corespunzător
                        print("\nNo cars available")
                    elif "cars" in response:
                        print("\nAvailable cars:")
                        for car_id, info in response["cars"].items():
                            status = "Available" if info["available"] else "Rented"
                            print(f"{car_id}: {info['model']} ({info['type']}) - {status}")
                    else:
                        print(f"Response: {response.get('message')}")

                # Handle other actions
                else:
                    client.send(json.dumps(req).encode("utf-8"))
                    response = response_queue.get(timeout=5)
                    print(f"Response: {response.get('message')}")

        except Exception as e:
            print(f"Error: {e}")
            break

    client.close()


if __name__ == "__main__":
    client_mobile()