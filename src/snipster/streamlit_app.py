"""Streamlit application for Snipster, a code snippet management tool."""

from typing import Any, Dict, List

import httpx
import streamlit as st
from fastapi import HTTPException

from snipster.cli import create_gist
from snipster.models import Language

API_URL = "http://localhost:8000/"

st.set_page_config(
    page_title="Snipster",
    page_icon=":memo:",
    layout="wide",
    initial_sidebar_state="expanded",
)

if "view_id" not in st.session_state:
    st.session_state.view_id = None

if "current_menu" not in st.session_state:
    st.session_state.current_menu = "List Snippets"

st.title("📝 Snipster - Code Snippet Manager")

menu = st.sidebar.radio(
    "Choose Action",
    (
        "Add Snippet",
        "Edit Snippet",
        "List Snippets",
        "Search Snippets",
        "Run Snippet",
        "Delete Snippet",
    ),
    index=(
        "Add Snippet",
        "Edit Snippet",
        "List Snippets",
        "Search Snippets",
        "Run Snippet",
        "Delete Snippet",
    ).index(st.session_state.current_menu),
)

# Update current_menu when radio selection changes
if menu != st.session_state.current_menu:
    st.session_state.current_menu = menu
    # Clear edit state when changing menus
    if "edit_snippet_id" in st.session_state:
        st.session_state.edit_snippet_id = None
    # Clear run state when changing menus
    if "run_snippet_id" in st.session_state:
        st.session_state.run_snippet_id = None
    if "auto_run" in st.session_state:
        st.session_state.auto_run = False

if (
    st.session_state.current_menu != "List Snippets"
    and st.session_state.view_id is not None
):
    st.session_state.view_id = None
    st.rerun()

if st.session_state.view_id is not None:
    snippet_id = st.session_state.view_id
    r = httpx.get(f"{API_URL}snippets/{snippet_id}")
    if not r.is_success:
        st.error("Snippet not found.")
        st.session_state.view_id = None
        st.rerun()
    else:
        snippet = r.json()
        st.markdown(
            f"## 🩹 {snippet['title']} {snippet['language']} {'🌟' if snippet['favorite'] else ''}"
        )
        st.markdown(snippet.get("description", ""))
        st.code(snippet["code"], language=snippet["language"])

        st.caption(f"Tags: {snippet.get('tags', '')}")

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("Toggle Favorite", key="toggle_favorite"):
                httpx.post(f"{API_URL}snippets/{snippet_id}/favorite")
                st.rerun()
        with col2:
            tags = st.text_input("Add tags (comma-separated)", key="tags_input")
            if st.button("Add Tags"):
                params = [tag.strip() for tag in tags.split(",") if tag.strip()]  # type: ignore
                httpx.post(f"{API_URL}snippets/{snippet_id}/tags", params=params)  # type: ignore
                st.rerun()
        with col3:
            if st.button("Remove Tags (comma-separated)", key="remove_tags"):
                params = [tag.strip() for tag in tags.split(",") if tag.strip()]  # type: ignore
                params.append(("remove", "true"))  # type: ignore
                httpx.post(
                    f"{API_URL}snippets/{snippet_id}/tags",
                    params=params,  # type: ignore
                )
                st.rerun()

        if st.button("🔄 Edit Snippet", key="edit_snippet"):
            st.session_state.current_menu = "Edit Snippet"
            st.session_state.edit_snippet_id = snippet_id
            st.rerun()

        if st.button("▶ Run Snippet", key="run_snippet"):
            st.session_state.current_menu = "Run Snippet"
            st.session_state.run_snippet_id = snippet_id
            st.session_state.auto_run = True
            st.session_state.view_id = None
            st.rerun()

        if st.button("❌ Delete Snippet", key="delete_snippet"):
            r = httpx.delete(f"{API_URL}snippets/{snippet_id}")
            if r.is_success:
                st.success("Snippet deleted successfully!")
            else:
                st.error("Failed to delete snippet.")
            st.session_state.view_id = None
            st.rerun()

        if st.button(" Gist Snippet", key="gist_snippet"):
            params = {
                "title": snippet["title"],
                "code": snippet["code"],
                "public": True,  # Default to public for simplicity
            }
            try:
                gist_url = create_gist(
                    **params,
                )
                st.success(f"Gist created successfully: {gist_url}")
            except HTTPException as e:
                raise HTTPException(status_code=500, detail=str(e)) from e
            except httpx.RequestError as e:
                st.error(f"Connection error: {str(e)}")

        if st.button("↩ Back to List", key="back_to_list"):
            st.session_state.view_id = None
            st.rerun()

elif st.session_state.current_menu == "List Snippets":
    st.header("📋 All Snippets")
    r = httpx.get(f"{API_URL}snippets/")
    if not r.is_success:
        st.error("Failed to fetch snippets.")
    else:
        snippets = r.json()
        if not snippets:
            st.info("No snippets found.")
        else:
            for snippet in snippets:
                col1, col2 = st.columns([6, 1])
                with col1:
                    label: str = f"{snippet['title']} [{snippet['language']}]"
                    if snippet["favorite"]:
                        label += " ⭐"
                    st.markdown(f"### {label}")
                    st.markdown(snippet.get("description", ""))
                    st.caption(f"Tags: {snippet.get('tags', '')}")
                with col2:
                    if st.button("View", key=f"view-{snippet['id']}"):
                        st.session_state.view_id = snippet["id"]
                        st.rerun()

elif st.session_state.current_menu == "Add Snippet":
    st.header("➕ Add Snippet")
    languages: List[str] = [language.value for language in Language]
    with st.form("add_snippet_form"):
        title = st.text_input("Title")
        code = st.text_area("Code")

        language = st.selectbox(
            "Language",
            # ["Python", "JavaScript", "Java", "C++", "Ruby", "Go", "Other"],
            languages,
        )

        description = st.text_input("Description (optional)")
        tags = st.text_input("Tags (comma-separated, optional)")

        submit_button = st.form_submit_button("Add")
        gist_button = st.form_submit_button("Create Gist")

        if submit_button:
            # Validate required fields
            if not title.strip():
                st.error("Title is required.")
            elif not code.strip():
                st.error("Code is required.")
            else:
                params = {
                    "title": title.strip(),
                    "language": language,
                    "code": code.strip(),
                }

                if description.strip():
                    params["description"] = description.strip()

                if tags.strip():
                    params["tags"] = "".join(
                        [tag.strip() for tag in tags.split(",") if tag.strip()]  # type: ignore
                    )

                # Debug: Show what we're sending
                # st.write("Debug - Sending to API:", params)

                try:
                    r = httpx.post(f"{API_URL}snippets/", json=params)  # type: ignore

                    # Debug: Show response details
                    # st.write(f"Debug - Response status: {r.status_code}")
                    # st.write(f"Debug - Response text: {r.text}")

                    if r.is_success:
                        st.success("Snippet added successfully!")
                        response_data = r.json()
                        # st.write("Debug - Response data:", response_data)

                        st.session_state.view_id = response_data.get("id", None)
                        st.session_state.current_menu = "List Snippets"
                        st.rerun()
                    else:
                        st.error(f"Failed to add snippet. Status: {r.status_code}")
                        try:
                            error_detail = r.json()
                            st.error(f"Error details: {error_detail}")
                        except ValueError:
                            st.error(f"Raw error: {r.text}")
                except httpx.RequestError as e:
                    st.error(f"Connection error: {str(e)}")
                    st.error(
                        "Make sure the API server is running on http://localhost:8000/"
                    )
        elif gist_button:
            # Handle Gist creation
            if not title.strip() or not code.strip():
                st.error("Title and code are required to create a Gist.")
            else:
                params: Dict[str, Any] = {
                    "title": title.strip(),
                    "code": code.strip(),
                    "public": True,  # Default to public for simplicity
                }
                try:
                    r = httpx.post(
                        f"{API_URL}snippets/gist/",
                        json=params,
                    )  # type: ignore
                    if r.is_success:
                        gist_url = r.json().get("url")
                        st.success(f"Gist created successfully! URL: {gist_url}")
                    else:
                        st.error(f"Failed to create Gist. Status: {r.status_code}")
                except httpx.RequestError as e:
                    st.error(f"Connection error: {str(e)}")

elif st.session_state.current_menu == "Edit Snippet":
    st.header("✏️ Edit Snippet")

    # Check if we have a snippet ID to edit
    if (
        "edit_snippet_id" not in st.session_state
        or st.session_state.edit_snippet_id is None
    ):
        st.error(
            "No snippet selected for editing. Please go back to the list and select a snippet to edit."
        )
        if st.button("Back to List"):
            st.session_state.current_menu = "List Snippets"
            st.rerun()
    else:
        snippet_id = st.session_state.edit_snippet_id

        # Fetch the current snippet data
        r = httpx.get(f"{API_URL}snippets/{snippet_id}")
        if not r.is_success:
            st.error("Snippet not found.")
            st.session_state.edit_snippet_id = None
            if st.button("Back to List"):
                st.session_state.current_menu = "List Snippets"
                st.rerun()
        else:
            snippet = r.json()
            languages: List[str] = [language.value for language in Language]

            with st.form("edit_snippet_form"):
                title = st.text_input("Title", value=snippet["title"])
                code = st.text_area("Code", value=snippet["code"], height=200)

                # Find current language index
                current_lang_index = 0
                if snippet["language"] in languages:
                    current_lang_index = languages.index(snippet["language"])

                language = st.selectbox("Language", languages, index=current_lang_index)

                description = st.text_input(
                    "Description (optional)", value=snippet.get("description", "")
                )

                # Handle tags - ensure it's a string for the input field
                current_tags_raw = snippet.get("tags", "")
                current_tags = ""
                if current_tags_raw:
                    if isinstance(current_tags_raw, str):
                        current_tags = current_tags_raw
                    else:
                        # Assume it's a list and convert safely
                        current_tags = ", ".join(map(str, current_tags_raw))

                tags = st.text_input(
                    "Tags (comma-separated, optional)", value=current_tags
                )

                col1, col2 = st.columns(2)
                with col1:
                    update_button = st.form_submit_button(
                        "Update Snippet", type="primary"
                    )
                with col2:
                    cancel_button = st.form_submit_button("Cancel")

                if update_button:
                    params = {"title": title, "language": language, "code": code}
                    if description:
                        params["description"] = description
                    if tags:
                        params["tags"] = [
                            tag.strip() for tag in tags.split(",") if tag.strip()
                        ]

                    r = httpx.put(f"{API_URL}snippets/{snippet_id}", json=params)  # type: ignore
                    if r.is_success:
                        st.success("Snippet updated successfully!")
                        st.session_state.view_id = snippet_id
                        st.session_state.edit_snippet_id = None
                        st.session_state.current_menu = "List Snippets"
                        st.rerun()
                    else:
                        st.error("Failed to update snippet.")

                if cancel_button:
                    st.session_state.view_id = snippet_id
                    st.session_state.edit_snippet_id = None
                    st.session_state.current_menu = "List Snippets"
                    st.rerun()

elif st.session_state.current_menu == "Search Snippets":
    st.header("🔍 Search Snippets")
    query = st.text_input("Search Query")
    language = st.selectbox(
        "Language",
        [lang.value for lang in Language] + ["All"],
        index=len(Language),  # "All" is the last option
    )

    if st.button("Search"):
        params = {"term": query}
        if language != "All":
            params["language"] = language
        r = httpx.get(f"{API_URL}snippets/search/", params=params)  # type: ignore
        if r.is_success:
            snippets = r.json()
            if not snippets:
                st.info("No snippets found.")
            else:
                for snippet in snippets:
                    col1, col2 = st.columns([6, 1])
                    with col1:
                        label: str = f"{snippet['title']} [{snippet['language']}]"
                        if snippet["favorite"]:
                            label += " ⭐"
                        st.markdown(f"### {label}")
                        st.markdown(snippet.get("description", ""))
                        st.caption(f"Tags: {snippet.get('tags', '')}")
                    with col2:
                        if st.button("View", key=f"view-{snippet['id']}"):
                            st.session_state.view_id = snippet["id"]
                            st.rerun()
                if st.button("Clear Search"):
                    st.session_state.view_id = None
                    st.rerun()
                if st.button("Back to List"):
                    st.session_state.view_id = None
                    st.rerun()
        else:
            st.error("Failed to search snippets.")

elif st.session_state.current_menu == "Run Snippet":
    st.header("▶ Run Snippet")

    # Check if we have a snippet ID to run (from navigation)
    default_snippet_id = ""
    if (
        "run_snippet_id" in st.session_state
        and st.session_state.run_snippet_id is not None
    ):
        default_snippet_id = f"{st.session_state.run_snippet_id}"

    snippet_id = st.text_input("Snippet ID", value=default_snippet_id)
    version = st.text_input("Language Version (optional, default is 3.10.0)")

    # Auto-run if we came from snippet view
    should_auto_run = (
        "auto_run" in st.session_state
        and st.session_state.auto_run
        and snippet_id
        and snippet_id.isdigit()
    )

    if st.button("Run") or should_auto_run:
        # Clear auto_run flag
        if "auto_run" in st.session_state:
            st.session_state.auto_run = False

        if not snippet_id.isdigit():
            st.error("Please enter a valid snippet ID.")
        else:
            params = {"version": version} if version else {}
            r = httpx.post(f"{API_URL}snippets/{snippet_id}/run", params=params)  # type: ignore
            if r.is_success:
                result = r.json()
                st.success("Code executed successfully!")
                st.code(result["output"], language="text")

                # Show snippet info
                snippet_r = httpx.get(f"{API_URL}snippets/{snippet_id}")
                if snippet_r.is_success:
                    snippet_info = snippet_r.json()
                    st.info(
                        f"Executed: {snippet_info['title']} [{snippet_info['language']}]"
                    )

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("View Snippet", key=f"view-{snippet_id}"):
                        st.session_state.view_id = snippet_id
                        st.session_state.current_menu = "List Snippets"
                        st.rerun()
                with col2:
                    if st.button("Back to List"):
                        st.session_state.current_menu = "List Snippets"
                        st.rerun()

                if result.get("stderr"):
                    st.error("Error Output:")
                    st.code(result["stderr"], language="text")
            else:
                st.error("Failed to run snippet. Please check the ID and try again.")

elif st.session_state.current_menu == "Delete Snippet":
    st.header("❌ Delete Snippet")
    snippet_id = st.text_input("Snippet ID to delete")

    if st.button("Delete"):
        if not snippet_id.isdigit():
            st.error("Please enter a valid snippet ID.")
        else:
            r = httpx.delete(f"{API_URL}snippets/{snippet_id}")
            if r.is_success:
                st.success("Snippet deleted successfully!")
                st.session_state.view_id = None
                st.rerun()
            else:
                st.error("Failed to delete snippet. Please check the ID and try again.")
else:
    st.error("Please select an action from the sidebar.")
