from app_modular import create_app, create_socketio

app = create_app()
socketio = create_socketio(app)

if __name__ == "__main__":
    socketio.run(app)
