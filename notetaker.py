# notetaker.py

import streamlit as st
import os

def save_note(note, filename):
    with open(filename, "w") as f:
        f.write(note)

def load_note(filename):
    if os.path.exists(filename):
        with open(filename, "r") as f:
            return f.read()
    return ""

def notetaker():
    st.subheader("Meeting Notetaker")

    # Initialize session state for notes
    if 'notes' not in st.session_state:
        st.session_state.notes = {}

    # Create a new note
    new_note_name = st.text_input("Enter a name for your note:")
    if new_note_name and new_note_name not in st.session_state.notes:
        st.session_state.notes[new_note_name] = ""

    # Select existing note
    note_names = list(st.session_state.notes.keys())
    selected_note = st.selectbox("Select a note to edit:", note_names, index=0 if note_names else None)

    if selected_note:
        # Edit note
        st.session_state.notes[selected_note] = st.text_area("Edit your note:", st.session_state.notes[selected_note], height=300)

        col1, col2, col3 = st.columns(3)

        # Save note
        if col1.button("Save Note"):
            save_note(st.session_state.notes[selected_note], f"{selected_note}.txt")
            st.success(f"Note '{selected_note}' saved successfully!")

        # Load note
        if col2.button("Load Note"):
            loaded_content = load_note(f"{selected_note}.txt")
            st.session_state.notes[selected_note] = loaded_content
            st.success(f"Note '{selected_note}' loaded successfully!")

        # Delete note
        if col3.button("Delete Note"):
            del st.session_state.notes[selected_note]
            if os.path.exists(f"{selected_note}.txt"):
                os.remove(f"{selected_note}.txt")
            st.success(f"Note '{selected_note}' deleted successfully!")
            st.experimental_rerun()

    # Display all notes
    st.subheader("All Notes")
    for note_name, note_content in st.session_state.notes.items():
        with st.expander(note_name):
            st.text_area("", note_content, height=100, key=f"display_{note_name}")

if __name__ == "__main__":
    notetaker()
