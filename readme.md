##How to set up Python with VS code
-Install Python: brew install python3
-Install Python extention

##How to set up your ENV:

Ctrl + Shft + P
>Python: Create Environment...
Choose Venv
Select the Global python interpreter (likely your only option)

Once you have the .venv folder close all terminals and reopen them you should see the below:

![Image](https://github.com/user-attachments/assets/f28aae32-5690-4300-8a64-7cae40c5c8fc)


Now run pip install -r requirements.txt

Start the server with:
uvicorn main:app --reload

Navigate to the URL:
http://127.0.0.1:8000/table/test_requests

GET TO WORK AHAHAHHAHA