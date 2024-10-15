from filecmp import clear_cache
from inspect import cleandoc
import streamlit as st
from supabase import create_client, Client
from functions import insert_user, question_count, get_last_email, send_answers, get_user_id_by_email, get_formatted_questions_and_answers, analyze_answers
import json

#1 Page configuration has to be on the first streamlit function call
st.set_page_config(layout="wide")
#2 Title of the page
st.title("Moral-Personality Test")
#3 First guidelines
st.write("There are 20 questions that shall decide your moral personality. Think well before answering.")
st.write("") # I add some space in some places for better experience

#4 Set up your Supabase URL and API Key using Streamlit Secrets
# the secrets have to be set on secrets.toml file or (in case of deploying) in your streamlit app website settings
supabase_url = st.secrets["SUPABASE_URL"] 
supabase_key = st.secrets["SUPABASE_KEY"] 

#5 Create the Supabase client
supabase: Client = create_client(supabase_url, supabase_key)
#6 Check for errors
response = supabase.table("users").select("*").execute()
if response.data is None:  # if no data is returned, there might be an error
    st.write(":red[An error occurred with the connection to the database. Please contact Bruno.]", "response: ", response)

st.write("")
st.write("")

#7 Initialize user_selections in session_state if not already present
if 'user_selections' not in st.session_state:
    st.session_state.user_selections = [None] * question_count()  # imported from functions.py
                                           # ^initialize as a list with none for each question

#8 Get the total number of questions from the table 'questions'
question_number = question_count()  
#9 Fetch actual questions from the 'questions' table
questions_response = supabase.table("questions").select("question_text").order("id").execute()
questions_list = [question["question_text"] for question in questions_response.data]
#10 Fetch alternatives from the 'possible_answers' table
answers_response = supabase.table("possible_answers").select("*").execute()

#11 Create a list of letters for labeling alternatives
letters = ['a)', 'b)', 'c)', 'd)', 'e)', 'f)', 'g)', 'h)', 'i)', 'j)']  # extend this list as needed

#12 Iterate through the questions and display the question number
for i in range(1, question_number + 1):
    st.write(f"**Question {i}. {questions_list[i-1]}**")

    # fetch the alternatives for the current question
    alternatives = [answer["Alternatives"] for answer in answers_response.data if answer["Question"] == i]

    # display each alternative with corresponding letter and a button for selection
    for index, alternative in enumerate(alternatives):
        if index < len(letters):  # check to avoid IndexError
            button_label = f"{letters[index]} {alternative}"
        else:
            button_label = f"{index + 1}) {alternative}"  # fallback for more than 10 alternatives
        
        # check if this alternative was previously selected
        if st.session_state.user_selections[i - 1] == button_label.split(" ")[0]:  # using i - 1 for zero-based index
            # use markdown to style the selected button
            st.markdown(f"<span style='color: white; background-color: red; padding: 10px; border-radius: 5px;'>{button_label}</span>", unsafe_allow_html=True)
        else:
            # create a button for each alternative
            if st.button(button_label, key=f"question_{i}_alternative_{index}"):
                # store the selection in the list
                st.session_state.user_selections[i - 1] = button_label.split(" ")[0]  # Store only the letter

    st.write("")  # add space between questions

#13 Display the user selections in the sidebar
# st.sidebar.write("User selections:", st.session_state.user_selections)
#14 Check if user selections are all filled
if all(selection is not None for selection in st.session_state.user_selections):
    # requesting user name and email
    name = [st.text_input(":gray[Your name]", key="NAME")]
    email = [st.text_input(":gray[Your email]", key="EMAIL")]
    st.write("")

#15 Check if user is ready to submit test and submit it
try:            # error until user finishes test
    if email == None: email = [""]
    if name == None: name = [""]
except NameError:
    email = [""]
    name = [""]
provide_answer = False # initialize trigger for providing analysis

if email[0] != "":
    if name[0] != "":
        # check if the email already exists in the database
        response = supabase.table('users').select('email').eq('email', email[0]).execute()
        # if the email does not exist, insert new user
        if not response.data:
            insert_user(name[0], email[0])  # insert user if email is not found
            print("########### New user created. ###########")
            response.data = [{'email': email[0]}] # collapsing 'response' possibilities for further use
            answer = False # initialize trigger for skipping another insertion
        else: 
            print("This email already exists: ", response.data[0]['email'])
            user_id = get_user_id_by_email()
            # retrieve ONLY THE FIRST past answer from the database. it doesn't search for other matches
            answer = supabase.table('answers').select('user_answer').eq('user_id', user_id).execute()
            answer = answer.data[0]['user_answer']
            if isinstance(answer, str): # If answer is a JSON string, convert it to a list
                answer = json.loads(answer)
            if answer == st.session_state.user_selections: answer = answer
            else: answer = False

        # retrieve the last email from the 'users' table
        last_email = get_last_email()  # why? I don't know

        # check if the input email is in the database, if yes, submit and return success
        if response.data[0]["email"] == email[0]:
            # send the answers to the database
            user_id = get_user_id_by_email()
            if answer == False:     # if the current answers don't match existing answers, input new answers
                if user_id:
                    print(f"########### User ID retrieved: {user_id} #############")
                    answer = st.session_state.user_selections
                    send_answers(answer, user_id)
                    st.success(f"**Your test was submitted, {name[0]}!**", icon="✅")
                    provide_answer = True # trigger for providing analysis 
                else:
                    st.warning("Error: user ID not found. Please input a name and a new email.")
            else:
                provide_answer = True # trigger for providing analysis 

    else:
        st.write(":red[This won't work if you don't input your name...]")
else:
    st.warning("Please answer all questions before proceeding.")

#16 Just a small tip
st.write("*Tip: You will know your answers are submitted when you see the* ✅.")

#17 Get questions and answers in a single string for LLM analysis
@st.cache_data()  # cache was messing with format, so if it's not working just take it out
def analyze_cached(questions, answers):
    return analyze_answers(questions, answers)

# call the cached function
if provide_answer:
    with st.spinner('Analysing Results...'):
        analysis = analyze_cached(get_formatted_questions_and_answers(), answer)  # using 'answer' variable

    st.write("**Your Analysis:**")
    st.write(analysis)
        
    #18 Get Feedback from user
    st.write("")
    st.write("I hope you have enjoyed this test.")
    st.write("**Any suggestions? Tell us what you think.**")
    feedback1 = st.text_input("", key="feedback")

    # initialize variables and catch mismatchs
    user_id = None
    try: user_id = get_user_id_by_email()
    except: user_id = None
    try:            # I don't really know why this is here...
        if email == None: email = [""]
        if name == None: name = [""]
    except NameError:
        email = [""]
        name = [""]

    #19 Insert feedback into 'feedback' table
    if feedback1 != "" and email[0] != "" and name[0] != "":
        # only insert feedback if user_id is found
        if user_id is not None:
            response = supabase.table("feedback").insert({
                "suggestions": feedback1,
                "user_id": user_id
            }).execute()

            # check for success
            if response.data:
                st.success("Thank you for the most useful feedback! No, seriously!")
                st.balloons()
            elif response.error:
                st.write(":red[An error occurred:]", response.error)
        else:
            st.write(":red[Cannot submit feedback without a valid user ID. Try filling your name and email address.]")
    elif feedback1 != "":
        st.write(":red[Please fill in your name and email to submit.]")

# Spinner Functionality: st.spinner()
# Waiting Functionality: time.sleep(1)
# Streaming strings Functionality: st.write_stream() and st.stream()

