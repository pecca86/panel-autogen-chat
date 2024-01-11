import panel as pn
from bokeh.plotting import figure

# Define the Panel template
template = pn.template.FastListTemplate(title='Panel Modal Example')


class MyAccordion(pn.Accordion):

    def get_accordion():
        custom_style = {
            'background': '#f9f9f9',
            'box-shadow': '5px 5px 5px #bcbcbc',
            'margin-top': '10px',  
            'color': 'black !important',
        }

        text_style = {
            'font-family': 'Arial',
            'font-size': '16px',
            'color': '#000000 !important',
        }

        area = pn.widgets.TextAreaInput(name='Known issues', auto_grow=True, max_rows=100, rows=50, value="""\n
        - Sometimes the chat inteface does not scroll all the way down, so you need to scroll manually.
        - Sometimes the loading indicator does not show up in the chat.
        - Currently, only the API Key & file input fields in the settings column are used. The other fields serve as placeholders for future development.
        - The current system is setup for a LinkedIn flow.
        - Uploaded file sizes can be up to 10MB. But having an agent with the current implementation going through 10MB of data will most likely hit the rate limits set for your OpenAI key.

        Any feedback is welcome! Please send an email to pekka.ranta-aho@weareida.digital.

        Last updated: 2.1.2024
        """, width=1000, height=300, disabled=False, styles=custom_style)




        accordion = pn.Accordion(('Info', area), styles=text_style)
        return accordion