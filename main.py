import os
import asyncio
import autogen
import panel as pn
import autogen
import shutil
from dotenv import load_dotenv

from ui_utils import AppUI

pn.extension(notifications=True)

file_name = ""
file_input = pn.widgets.FileInput(accept='.csv,.json,.pdf,.txt,.md', name='Upload File', visible=False)

def setup():
    load_dotenv()
    main()
    
def main():
    ui = AppUI()
    hide_loader_css = """
        .loader.light {
            display: none;
        }
        """

    # Apply the custom CSS to the current application
    pn.config.raw_css.append(hide_loader_css)
    
    #---------------------------------
    # T W I T T E R  I N T E R F A C E
    #---------------------------------
    twitter_chat_interface = ui.get_twitter_chat()
    twitter_chat_interface.visible = False

    #-----------------------------------
    # L I N K E D I N  I N T E R F A C E
    #-----------------------------------
    linked_in_chat_interface = ui.get_linked_in_chat(file_input, agent_temperature=0.5)
    linked_in_chat_interface.visible = False

    #-------------------------------------
    # C O M P O N E N T  F U N C T I O N S
    #-------------------------------------
    def activate_rag(event):
        enabled = rag_switch.value
        ui.set_rag(enabled)
        file_input.visible = not file_input.visible
    
    def set_temperature(event):
        global agent_temperature
        agent_temperature = temp_slider.value
  
    def append_chat(env):
        linked_in_chat_interface.clear()
        twitter_chat_interface.clear()
        if flow_selector.value == "LinkedIn":
            print("LinkedIn selected")
            linkedin_column.visible = True
            twitter_column.visible = False
            twitter_chat_interface.visible = False
            linked_in_chat_interface.visible = True
            linked_in_chat_interface.send("Thanks for selecting Linked In. Please type in to the chat what sort of an Linked In post you would like to create. You also have the option on selecting the RAG agent to enable me to learn more on the subject from a document of yours. 🦉", user="System", respond=False)
        elif flow_selector.value == "Twitter":
            print("Twitter selected")
            twitter_column.visible = True
            linkedin_column.visible = False
            linked_in_chat_interface.visible = False
            twitter_chat_interface.visible = True
            twitter_chat_interface.send("Thanks for selecting Twitter! Type in anything you would like me to create a tweet about! 🐥", user="System", respond=False)

    flow_selector = pn.widgets.Select(options=['', 'LinkedIn', 'Twitter', 'Instagram', 'Facebook', 'Web Page'], name='Target Platform')
    pn.bind(append_chat, flow_selector, watch=True)

    temp_slider = pn.widgets.FloatSlider(name='Creativity (0 low, 1 high)', start=0, end=1, value=0.5)
    pn.bind(set_temperature, temp_slider, watch=True)
    rag_switch = pn.widgets.Switch(name='Switch', align='center')
    pn.bind(activate_rag, rag_switch, watch=True)
    rag_switch_label = pn.pane.Markdown("Activate RAG Agent")
    labeled_switch = pn.Row(rag_switch_label, rag_switch)

    # FILE INPUT
    # delete all files in the folder first
    def delete_files(env=None):
        folder = './uploaded_files/'
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                file_input.disabled = False
                update_uploaded_files()
            except Exception as e:
                print('Failed to delete %s. Reason: %s' % (file_path, e))

    delete_files()

    file_column = pn.Column(width=300)
    def update_uploaded_files():
        file_column.clear()
        for filename in os.listdir('./uploaded_files/'):
            row = pn.Row()
            delete_btn =  pn.widgets.Button(name="Delete", button_type="danger")
            pn.bind(delete_files, delete_btn, watch=True)
            file = pn.widgets.StaticText(name="File", value=filename, align="center", max_width=230)
            row.append(file)
            row.append(delete_btn)
            file_column.append(row)

    update_uploaded_files()

    def save_file(event):
        global file_name
        file_name = file_input.filename # so the RAG agent can find it

        # check if file already exists in ./uploaded_files/, if so do not save it
        if os.path.exists(f"./uploaded_files/{file_name}"):
            pn.state.notifications.position = "top-center"
            pn.state.notifications.warning("File already exists!", duration=2500)
            file_input.value = None
            return

        print("Saving file...")
        uploaded_filename = file_input.filename
        file_byte_string = file_input.value
        save_path = './uploaded_files/'  # Replace with desired path

        os.makedirs(save_path, exist_ok=True)
        full_save_path = os.path.join(save_path, uploaded_filename)
        
        with open(full_save_path, 'wb') as file_to_write:
            file_to_write.write(file_byte_string)

        print(f'File "{uploaded_filename}" saved at "{full_save_path}"')
        pn.state.notifications.position = "top-center"
        pn.state.notifications.success("File uploaded successfully!", duration=2500)
        file_input.disabled = True
        update_uploaded_files()

    # Attach the save function to the value parameter
    file_input.param.watch(save_file, 'value')
    
    # Uploaded files
    uploaded_files_txt = pn.widgets.StaticText(name='Uploaded File', value='')

    linkedin_column = pn.Column(temp_slider, labeled_switch, file_input, uploaded_files_txt, file_column)
    linkedin_column.visible = False
    twitter_column = pn.Column(temp_slider)
    twitter_column.visible = False 

    logout = pn.widgets.Button(name="Log out")
    logout.js_on_click(code="""window.location.href = './logout'""")

    spinner = pn.indicators.LoadingSpinner(value=True, align="center", width=50, height=50, name="loading...")


    template = pn.template.MaterialTemplate(
        title="iDA Autogen Chat",
        sidebar=[logout, "Settings", flow_selector, linkedin_column, twitter_column],
        main=[twitter_chat_interface, linked_in_chat_interface],
    )
    template.servable()

if __name__ == "__main__":
    setup()

setup()
