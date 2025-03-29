# Car Sharing Application
This project implements a client-server architecture for a CarSharing system, allowing users to authenticate, rent cars, drive, and finalize rentals with payment processing. It also includes a car client for managing car states (e.g., locked/unlocked).

## Features
### User Operations

* Register:
  * Users can create a new account with a username, password, and driver's license.

* Login/Logout:
  * Users can log in to access car rental services and log out when done.

* Query Cars:
  * View available cars for rent.

* Select Car:
  * Reserve a specific car.

* Start Rental:
  * Initiate the car rental process.

* Drive:
  * Unlock and drive the rented car.

* End Rental:
  * Finalize the rental and proceed to payment.

* Payment:
  * Users must complete the payment to finish the rental process.

### Car Operations

* Register Car:
  * Cars register with the server and are tracked.

* Report State:
  * Cars periodically report their status (locked/unlocked).

* Check Car State: 
  * Verify the current state of a car.

* Toggle Car Lock:
  * Lock or unlock a car remotely.

### System Components

* Server:
  * Handles user authentication, car availability, and rental management.

* ClientApp:
  * The mobile application interface for users.

* ClientCar:
  * Represents a car, manages its state, and communicates with the server.

### Data Storage

The system uses the following files for persistent storage:

* users.txt:
  * Stores user credentials and license information.

* cars.txt:
  * Maintains car information (ID, model, type, and availability).

* rentals.txt:
  * Tracks active rentals (user-to-car mapping).

### How It Works

#### User Authentication

* Users register or log in to the system.

#### Car Query & Selection

* Logged-in users can view and select available cars.

#### Rental Process

* Users start a rental, and the selected car is marked as unavailable.

* Users can unlock and drive the car.

#### Ending Rental & Payment

* Users end their rental, and the car is marked available again.

* Users must complete payment to finalize the rental.

#### Car Communication

* Cars report their state and receive lock/unlock commands.
