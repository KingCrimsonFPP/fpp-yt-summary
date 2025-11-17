from bs4 import BeautifulSoup

# Read the HTML file
with open('transcript.html', 'r', encoding='utf-8') as file:
    html_content = file.read()

# Parse the HTML
soup = BeautifulSoup(html_content, 'html.parser')

# Find all yt-formatted-string elements
yt_strings = soup.find_all('yt-formatted-string')

# Open transcribed.txt in write mode
with open('transcribed.txt', 'w', encoding='utf-8') as output_file:
    for element in yt_strings:
        text = element.get_text()
        if text.strip():  # Only write non-empty strings
            output_file.write(text + '\n')