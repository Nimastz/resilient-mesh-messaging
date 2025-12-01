# services/routing_service/main.py
import uvicorn


def main():
    """
    Entry point for the routing & store-and-forward service (Person 2).

    It runs the FastAPI app defined in api.py.
    The app:
      - initializes the SQLite queue
      - starts the background routing loop
      - exposes internal APIs:
          POST /enqueue_message
          GET  /outgoing_chunks
          POST /mark_delivered
    """
    
    uvicorn.run(
        "services.routing_service.api:app",
        host="0.0.0.0",
        port=9002,
        reload=True,  
    )


if __name__ == "__main__":
    main()
