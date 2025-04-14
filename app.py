import streamlit as st
import pandas as pd
import numpy as np


st.title("Warga Naget's Portofolio Website")
st.write("Welcome to my portofolio website")

container = st.container()
with container:
    st.subheader("About me")

chart_data = pd.DataFrame(np.random.randn(20, 3), columns=["a", "b", "c"])

st.area_chart(chart_data)

prompt = st.chat_input("Say something")
if prompt:
    st.write(f"User has sent the following prompt: {prompt}")

st.title("Camera Demo 📸")

enable = st.checkbox("Enable camera")
picture = st.camera_input("Take a picture", disabled=not enable)

if picture:
    st.image(picture, caption="Here is your photo!", use_column_width=True)