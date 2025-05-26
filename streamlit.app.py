import streamlit as st
import requests
import json
import os

def get_server_data():
    # Simulate fetching the dictionary from the API
    return {
        "1365519077786914877": {
            "key": "nuh uh",
            "open": False,
            "ticket-open-message": "Click the button to create a ticket!",
            "ticket-category": "Support",
            "ticket-channel": "ticket-",
            "ticket-message": "Hello {{user}}, a <@1365520086961619025> will be with you shortly. Please provide as much detail as possible on your problem.",
            "auto-rename": False,
            "user-close": False,
            "staff-id": 1365520086961619025,
            "whitelist": False,
            "role-id": 1365523762354585620,
            "ticket-transcribe": True,
            "transcript": 1365525180528594994
        }
    }
st.set_page_config(page_title="Server Configurations", page_icon="🗂️")
st.title("Edit Server Configurations")

# Form to edit servers.json
with st.form("edit_config_form"):
    st.subheader("Update Server Configuration")

    solikekey = st.text_input("Key", placeholder="Enter the server key", help="The unique identifier for the server.")
    change_key = st.selectbox(
        "Change Key",
        options=[
            "ticket-open-message", "ticket-category", "ticket-channel", "ticket-message",
            "auto-rename", "user-close", "staff-id", "whitelist", "role-id", "ticket-transcribe", "transcript"
        ],
        help="Select the configuration key you want to update."
    )

    input_types = {
        "ticket-open-message": "text",
        "ticket-category": "text",
        "ticket-channel": "text",
        "ticket-message": "text",
        "auto-rename": "selectbox",
        "user-close": "selectbox",
        "staff-id": "number",
        "whitelist": "selectbox",
        "role-id": "number",
        "ticket-transcribe": "selectbox",
        "transcript": "number"
    }

    input_args = {
        "ticket-open-message": {"placeholder": "Enter the new message"},
        "ticket-category": {"placeholder": "Enter the new category"},
        "ticket-channel": {"placeholder": "Enter the new channel prefix"},
        "ticket-message": {"placeholder": "Enter the new ticket message"},
        "auto-rename": {"options": [True, False]},
        "user-close": {"options": [True, False]},
        "staff-id": {"value": 0},
        "whitelist": {"options": [True, False]},
        "role-id": {"value": 0},
        "ticket-transcribe": {"options": [True, False]},
        "transcript": {"value": 0}
    }
    if change_key:
        if input_types[change_key] == "text":
            value = st.text_input("Value", key=f"value_text_{change_key}", **input_args[change_key])
        elif input_types[change_key] == "number":
            value = st.number_input("Value", key=f"value_number_{change_key}", **input_args[change_key])
        elif input_types[change_key] == "selectbox":
            value = st.selectbox("Value", key=f"value_selectbox_{change_key}", **input_args[change_key])
        else:
            st.error("Invalid input type. Please check the configuration key.")

    # Submit button
    submitted = st.form_submit_button("Update Configuration")

    if submitted:
        # Send POST request to the API endpoint
        api_url = "http://212.192.29.158:25200/update-config"  # Replace with the actual API URL
        payload = {
            "key": solikekey,
            "change": change_key,
            "value": value
        }

        try:
            response = requests.post(api_url, json=payload)
            if response.status_code == 200:
                st.success("Configuration updated successfully!")
            elif response.status_code == 403:
                st.error(f"Unauthorized: Invalid key. Please check your server key. '{solikekey}'")
            else:
                st.error(f"Error: {response.status_code} - {response.text}")
        except requests.exceptions.RequestException as e:
            st.error(f"Request failed: {e}. Please check your network connection and try again.")
