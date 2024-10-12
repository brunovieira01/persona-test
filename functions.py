import streamlit as st
import supabase
from supabase import create_client, Client

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def insert_user(name: str, email: str):
  # Insert data into the users table
  response = supabase.table("users").insert({"name": name, "email": email}).execute()
  # Check for errors in the response and raise an exception if needed
  if response.data:
    print("User inserted successfully:", response.data)
  else:
    # Raise an error if the insertion was not successful
    error_message = response.error.get("message") if response.error else st.write("Try using a different email.")
    raise RuntimeError(f"Failed to insert user: {error_message}")

# Function to get the value of the last inserted email  
def get_last_email():
    """
    Retrieve the most recent email from the 'users' table.

    Returns:
    - email (str or None): The most recent email if found, otherwise None.
    """
    response = supabase.table("users").select("email").order("id", desc=True).limit(1).execute()
    
    # Check if the response contains data and extract the email
    if response.data and len(response.data) > 0:  # Ensure there's at least one email
        return response.data[0]['email']  # Return the email from the first row
    else:
        print("No email found in the response.")
        return None  # Return None if no email is found

# Function to get the number of rows in the 'questions' table
def question_count():
    response = supabase.table("questions").select("*", count="exact").execute()

    # Check for errors
    if response.data:
        return len(response.data)  # Count of rows in the 'questions' table
    else:
        st.error(f"Error retrieving questions: {response.error}")
        return 0  # Return 0 if there was an error

# Function to get the user ID from the 'users' table using the last email
def get_user_id_by_email():
    """
    Retrieve the user ID from the 'users' table using the last email.

    Returns:
    - user_id (int or None): The ID of the user if found, otherwise None.
    """
    # Get the last email using the existing function
    last_email = get_last_email()  # Now returns a string or None

    if last_email:
        # Query the 'users' table to find the user with the specified email
        response = supabase.table('users').select('id').eq('email', last_email).execute()

        # Check if the response contains data
        if response.data and len(response.data) > 0:
            return response.data[0]['id']  # Get the 'id' from the first row of data
        else:
            print("No user found with the specified email.")
            return None  # Return None if user not found
    else:
        print("Last email is None or invalid.")
        return None  # Return None if no last email is available



# Function to send answers to database
import json

def send_answers(user_selections, user_id):
    """
    Send user selections as a single row to the 'answers' table.

    Parameters:
    - user_selections (list): The list of user selections to be sent to the 'user_answer' column.
    - user_id (int): The ID of the user to be sent to the 'user_id' column.
    """
    # Ensure that user_selections is not empty and user_id is provided
    if not user_selections or user_id is None:
        return
    
    # Convert the user_selections list to a JSON string (or comma-separated string if preferred)
    user_answer_str = json.dumps(user_selections)

    # Prepare the data for insertion
    data_to_insert = {
        "user_answer": user_answer_str,  # Store the list as a JSON string in the database
        "user_id": user_id
    }

    # Insert the data into the 'answers' table as a single row
    response = supabase.table("answers").insert(data_to_insert).execute()

    # Check if the response contains data
    if response.data:
        print("Answers inserted successfully:", response.data)
    else:
        # Handle the case where insertion failed (no data in response)
        error_message = response.get("message", "Unknown error occurred during insertion")
        print("Error inserting answers:", error_message)
        raise RuntimeError(f"Failed to insert answers: {error_message}")

    # Return response for further handling or logging (optional)
    return response
