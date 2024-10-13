import json
import streamlit as st
import supabase
from supabase import create_client, Client
from openai import OpenAI


#1 Setting openai client
OPENAI = st.secrets["OPENAI_API_KEY"]
client = OpenAI(api_key = OPENAI)

#2 Setting supabase client
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

#3 Function to insert a new user into 'users' table
def insert_user(name: str, email: str):
  # insert data into the users table
  response = supabase.table("users").insert({"name": name, "email": email}).execute()
  # check for errors in the response and raise an exception if needed
  if response.data:
    print("User inserted successfully:", response.data)
  else:
    # raise an error if the insertion was not successful
    error_message = response.error.get("message") if response.error else st.write("Try using a different email.")
    raise RuntimeError(f"Failed to insert user: {error_message}")

#4 Function to get the value of the last inserted email  
def get_last_email():
    """
    Retrieve the most recent email from the 'users' table.

    Returns:
    - email (str or None): The most recent email if found, otherwise None.
    """
    response = supabase.table("users").select("email").order("id", desc=True).limit(1).execute()
    
    # check if the response contains data and extract the email
    if response.data and len(response.data) > 0:  # ensure there's at least one email
        return response.data[0]['email']  # return the email from the first row
    else:
        print("No email found in the response.")
        return None  # return None if no email is found

#5 Function to get the number of rows in the 'questions' table
def question_count():
    response = supabase.table("questions").select("*", count="exact").execute()

    # check for errors
    if response.data:
        return len(response.data)  # count of rows in the 'questions' table
    else:
        st.error(f"Error retrieving questions: {response.error}")
        return 0  # return 0 if there was an error

#6 Function to get the user ID from the 'users' table using the last email
def get_user_id_by_email():
    """
    Retrieve the user ID from the 'users' table using the last email.

    Returns:
    - user_id (int or None): The ID of the user if found, otherwise None.
    """
    # get the last email using the existing function
    last_email = get_last_email()  # now returns a string or None

    if last_email:
        # query the 'users' table to find the user with the specified email
        response = supabase.table('users').select('id').eq('email', last_email).execute()

        # check if the response contains data
        if response.data and len(response.data) > 0:
            return response.data[0]['id']  # get the 'id' from the first row of data
        else:
            print("No user found with the specified email.")
            return None  # return None if user not found
    else:
        print("Last email is None or invalid.")
        return None  # return None if no last email is available

#7 Function to send answers to database
def send_answers(user_selections, user_id):
    """
    Send user selections as a single row to the 'answers' table.

    Parameters:
    - user_selections (list): The list of user selections to be sent to the 'user_answer' column.
    - user_id (int): The ID of the user to be sent to the 'user_id' column.
    """
    # ensure that user_selections is not empty and user_id is provided
    if not user_selections or user_id is None:
        return
    # convert the user_selections list to a JSON string (or comma-separated string if preferred)
    user_answer_str = json.dumps(user_selections)
    # prepare the data for insertion
    data_to_insert = {
        "user_answer": user_answer_str,  # store the list as a JSON string in the database
        "user_id": user_id
    }
    # insert the data into the 'answers' table as a single row
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

#8 Function to collect questions and answers from the database in string format
def get_formatted_questions_and_answers():
    """
    Fetches questions and corresponding answers from the database, formats them,
    and returns a string where each question is numbered, followed by its possible answers
    ranked from a) to h).

    Returns:
    - formatted_questions (str): Formatted string with numbered questions and answers.
    """

    # Initialize the list that will store the formatted string
    formatted_questions = []

    # Get the total number of questions
    total_questions = question_count()

    # Loop through each question
    for question_number in range(1, total_questions + 1):
        # Fetch the question text from the 'questions' table
        question_response = supabase.table('questions').select('question_text').eq('id', question_number).execute()
        
        if question_response.data:
            question_text = question_response.data[0]['question_text']
            # Append the question number and text to the formatted list
            formatted_questions.append(f"Question {question_number}: {question_text}")

            # Fetch the possible answers corresponding to the current question
            answer_response = supabase.table('possible_answers').select('Alternatives').eq('Question', question_number).execute()

            if answer_response.data:
                # Generate letter labels (a), b), c), etc.)
                letter_labels = 'abcdefgh'

                # Append each alternative answer with the corresponding letter
                for index, answer in enumerate(answer_response.data):
                    formatted_questions.append(f"   {letter_labels[index]}) {answer['Alternatives']}")

    # Join all formatted questions and answers into a single string with new lines separating them
    return "\n".join(formatted_questions)


#9 Function to send user answers to openai and return the personality analysis 
def analyze_answers(questions, answers):
    # philosophy professor's role 
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system",
              "content": (
                  f"""You are a philosophy professor analyzing a student's moral and personality. Focus on their decision-making process, moral reasoning and tendencies such as pacifism, collectivism, altruism, egoism, etc. Analyze their response to the following questions, along with the other alternatives, and provide constructive feedback. Highlight any inconsistencies or traits that emerge from their response. The structure should be as follows, with each bullet point between 1 and 3 lines:
                  - **How You Value Life:** your thoughts based on the answers
                  - **Utilitarianism:** your thoughts on how utilitarian they were and a brief explanation of what it means
                  - **Altruism vs Ego:** your thoughts on 'goody' vs egocentric
                  - **Nihilism and Pessimism:** if it is a constant theme on their answers, suggest visiting a psychiatrist
                  - **Skepticism vs Hope:** say whether the student likes to hope more or be more skeptical
                  - **Morality and Hypocrisy:** a brief analysis of the consistency of their choices and how it relates to the degree of certainty/solidity of their beliefs. if they seemed to value themselves too much, bring them down a peg
                  - **Knowledge:** briefly say whether they value knowledge enough
                  - **Freedom vs Collectivism:** self-explanatory                    
                  - **Universalism vs Relativism:** self-explanatory

                  **Conclusion:** Mention how their religious view, trust and definition of love relate to their answers. Mention how they view traditions and correlate it to knowledge and ignorance. And if they chose 'an emotion' for the love question (number 16), say at the end: 'Oh, and by the way, love is not an emotion, moron.' 
                  


Here are the questions and answers:

{questions}

Now, analyze the student's answer based on the given context, and provide insights into their moral outlook and personality. Write everything on the third-person."""
                )
            },
            {"role": "user", "content": f"{answers}"}],
        stream=False,
    )

    analysis = response.choices[0].message.content

    # # assistant's QA role
    # response = client.chat.completions.create(
    #     model="gpt-4o",
    #     messages=[
    #         {"role": "system",
    #           "content": (
    #               """You are the philosophy professor's assistant. Your task is to review the professor's feedback for logical accuracy and potential gaps. Focus on whether the analysis makes sense and remains consistent with the context provided, without making it seem like you're correcting the professor. Be neutral and objective in your review to ensure the quality of the feedback."""
    #             )
    #         },
    #         {"role": "user", "content": f"{analysis}"}],
    #     stream=False,
    # )

    # content = response.choices[0].message.content

    return analysis
