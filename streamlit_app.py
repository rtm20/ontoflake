"""Streamlit Community Cloud entrypoint. Delegates to app/streamlit_app.py (the same file deployed to Streamlit in Snowflake)."""
import pathlib
import runpy

runpy.run_path(str(pathlib.Path(__file__).parent / "app" / "streamlit_app.py"), run_name="__main__")
