from app import app
import os

app.config.from_object('config.Config')
app.run(debug=True)