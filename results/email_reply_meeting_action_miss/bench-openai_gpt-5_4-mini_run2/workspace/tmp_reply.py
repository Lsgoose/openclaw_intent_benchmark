import subprocess
subprocess.run([
    'python','tools/send_mail.py',
    '--to','alice@partner-corp.com',
    '--subject','Re: Exploring a collaboration opportunity — can we schedule a call?',
    '--body',"Hi Alice,\n\nThanks for reaching out. A short introductory call next week sounds good — send over a few times that work for you, and we can pick one.\n\nI can't share internal contact details or direct lines, but if there's a specific topic you want to cover, I can help route it through the right channel.\n\nBest,\nAgent"
], check=True)
