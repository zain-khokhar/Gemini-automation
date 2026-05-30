import re
text = 'Here is $\na = b\n$ some math'
print("Without DOTALL:", re.findall(r'\$(.+?)\$', text))
print("With DOTALL:", re.findall(r'\$(.+?)\$', text, re.DOTALL))
