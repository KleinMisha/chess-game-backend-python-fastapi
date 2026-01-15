# Chess game backend 

## Learning goals
Learn how to create a full-stack application.
To achieve this, I will make my own multiplayer chess game. I will use this as an opportunity to separately create a backend and frontend, and eventually make multiple versions in different programming languages. 

**In this repository**
- **backend** - **Python** 
- Learn how to use fastAPI to create REST API.
- Learn how to make a very simple (in memory) SQL database using sqlalchemy
- This backend will handle calculating the 'state' of a chess game. That is, it will produce all information needed for any frontend application to create the view for the user to interact with. 


## Design process

After a couple of iterations of carefully designing the full-stack application such that I minimize coupling, I came to the conclusion that the cleanest way is to define the following layers in the backend:

* **API layer** : Defines the router(s) (fastAPI), and the format of request and response data (JSON format) using Pydantic
* **Service layer**:  Interface that translates data from the database/persistence layer, calls the game engine (domain layer), and translates things from/to formats that the API layer works with. 
* **Database/Persistence layer**: Defines database schema (sqlalchemy) and defines how we can write game states between turns.
* **Game/Domain layer**: The actual game logic lives here. 

Any additional cross-cutting concerns will be placed in a directory called `/src/core` (configuration settings, logging, etc.).

The game and database layer will be injected into the service layer. The service layer is injected into the api layer. This will allow me to build the layers independently of each other. This also makes it easy to test. 
All tests are placed in `/tests`, which will follow the exact same folder structure as the `/src` code. 

The main entrypoint of the application will be `main.py`, which will be responsible for creating the fastAPI application and starting it (and creating additional objects as needed).

Having defined the overall architecture, and have taken notes on what functions/files I will need in each layer, I can start coding. I will do this in reverse order, that is, starting from the lowest layer (the game logic), and work my way upwards to eventually the API later. 


