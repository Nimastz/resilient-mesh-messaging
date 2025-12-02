# services/crypto_service/main.py
import uvicorn 


def main():

    uvicorn.run(
        "services.crypto_service.api:app",
        host="0.0.0.0",
        port=7001,
        reload=True,
    )


if __name__ == "__main__":
    main()
