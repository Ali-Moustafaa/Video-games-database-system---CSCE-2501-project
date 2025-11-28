import streamlit as st
import mysql.connector
import pandas as pd
import plotly.express as px
import datetime

# DATABASE CONNECTION CONFIGURATION
DB_CONFIG = {
    "host": st.secrets["mysql"]["host"],
    "user": st.secrets["mysql"]["user"],
    "password": st.secrets["mysql"]["password"],
    "database": st.secrets["mysql"]["database"],
    "port": 3306
}

# HELPER FUNCTIONS

def get_connection():
    """Creates and returns a connection to the remote MySQL database."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        st.error(f"Error connecting to database: {err}")
        return None

def run_query(query, params=None):
    """Executes a query and returns the result as a Pandas DataFrame."""
    conn = get_connection()
    if conn:
        try:
            df = pd.read_sql(query, conn, params=params)
            conn.close()
            return df
        except Exception as e:
            st.error(f"Query failed: {e}")
            conn.close()
            return pd.DataFrame()
    return pd.DataFrame()

def run_transaction(query, params):
    """Executes an INSERT/UPDATE query."""
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except mysql.connector.Error as err:
            st.error(f"Transaction failed: {err}")
            conn.close()
            return False
    return False

# PAGE LAYOUT & STYLING
st.set_page_config(page_title="VGDB Manager", layout="wide", page_icon="🎮")

st.title("🎮 Video Games Database Manager")
st.markdown("---")

# Sidebar Navigation
menu = st.sidebar.radio(
    "Navigation",
    ["User Registration", "Rate Games", "My Ratings", "Game Browser", "Top Charts", "Dream Game Builder", "Director Analytics", "Platform Stats"]
)

# 1- REGISTER USER
if menu == "User Registration":
    st.header("📝 Register New User")
    with st.form("register_form"):
        col1, col2 = st.columns(2)
        with col1:
            new_username = st.text_input("Username")
            new_email = st.text_input("Email")
            new_gender = st.selectbox("Gender", ["Male", "Female", "Non-binary", "Prefer not to say"])
        with col2:
            new_age = st.number_input("Age", min_value=13, max_value=100)

            min_date = datetime.date(1900, 1, 1)
            max_date = datetime.date.today()
            default_date = datetime.date(2000, 1, 1)

            new_birthdate = st.date_input("Birthdate", value=default_date, min_value=min_date, max_value=max_date)
            # -----------------------------

            new_country = st.text_input("Country")

        submit = st.form_submit_button("Register")

        if submit:
            if new_email and new_username:
                query = """
                        INSERT INTO User (username, email, gender, age, birthdate, country)
                        VALUES (%s, %s, %s, %s, %s, %s) \
                        """
                success = run_transaction(query, (new_username, new_email, new_gender, new_age, new_birthdate, new_country))
                if success:
                    st.success(f"User {new_username} registered successfully!")
            else:
                st.warning("Email and Username are required.")

# 2- ADD RATING
elif menu == "Rate Games":
    st.header("⭐ Rate a Game")

    # Step 1: Select User
    user_email = st.text_input("Enter your Email to login:")

    if user_email:
        # Verify user exists
        user_check = run_query("SELECT * FROM User WHERE email = %s", (user_email,))
        if not user_check.empty:
            st.success(f"Welcome back, {user_check.iloc[0]['username']}!")

            # Step 2: Find Game to Rate
            search_term = st.text_input("Search for a game to rate:")
            if search_term:
                games = run_query("SELECT game_name, initial_release_date FROM Video_game WHERE game_name LIKE %s LIMIT 10", (f"%{search_term}%",))

                if not games.empty:
                    # Create a selection list
                    game_options = [f"{row['game_name']} ({row['initial_release_date']})" for index, row in games.iterrows()]
                    selected_game_str = st.selectbox("Select Game", game_options)

                    # Extract real values from selection
                    selected_idx = game_options.index(selected_game_str)
                    sel_game_name = games.iloc[selected_idx]['game_name']
                    sel_release_date = str(games.iloc[selected_idx]['initial_release_date'])

                    rating_val = st.slider("Your Rating", 1.0, 10.0, 5.0, 0.1)

                    if st.button("Submit Rating"):
                        query = """
                                INSERT INTO User_Rating (email, game_name, initial_release_date, rating_score, rating_date)
                                VALUES (%s, %s, %s, %s, CURDATE()) \
                                """
                        success = run_transaction(query, (user_email, sel_game_name, sel_release_date, rating_val))
                        if success:
                            st.balloons()
                            st.success("Rating submitted!")
                else:
                    st.info("No games found.")
        else:
            st.error("User not found. Please register first.")

# 3- VIEW RATINGS
elif menu == "My Ratings":
    st.header("📜 My Rating History")
    user_email = st.text_input("Enter your Email:")
    if user_email:
        query = """
                SELECT game_name, initial_release_date, rating_score, rating_date
                FROM User_Rating WHERE email = %s ORDER BY rating_date DESC \
                """
        df = run_query(query, (user_email,))
        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No ratings found for this user.")

# 4- GAME BROWSER (Filters)
elif menu == "Game Browser":
    st.header("🔍 Browse Games")


    col1, col2, col3, col4 = st.columns(4)

    with col1:
        # Fetch unique genres
        genres = run_query("SELECT DISTINCT genre_name FROM Genre")
        sel_genre = st.selectbox("Filter by Genre", ["All"] + genres['genre_name'].tolist())

    with col2:
        platforms = run_query("SELECT DISTINCT platform_name FROM Platform")
        sel_platform = st.selectbox("Filter by Platform", ["All"] + platforms['platform_name'].tolist())

    # The list of companies is fetched once to use for both Developer and Publisher filters
    companies = run_query("SELECT DISTINCT name FROM Company ORDER BY name")

    with col3:
        sel_dev = st.selectbox("Filter by Developer", ["All"] + companies['name'].tolist())

    with col4:
        sel_pub = st.selectbox("Filter by Publisher", ["All"] + companies['name'].tolist())

    # Build Query Dynamically
    base_query = """
                 SELECT v.game_name, v.initial_release_date, v.moby_score, v.critics_rating, v.players_rating
                 FROM Video_game v
                          LEFT JOIN Video_game_genre vg ON v.game_name = vg.game_name AND v.initial_release_date = vg.initial_release_date
                          LEFT JOIN Video_game_platform vp ON v.game_name = vp.game_name AND v.initial_release_date = vp.initial_release_date
                          LEFT JOIN Video_game_developer vd ON v.game_name = vd.game_name AND v.initial_release_date = vd.initial_release_date
                          LEFT JOIN Video_game_publisher vp_pub ON v.game_name = vp_pub.game_name AND v.initial_release_date = vp_pub.initial_release_date
                 WHERE 1=1 \
                 """
    params = []

    if sel_genre != "All":
        base_query += " AND vg.genre_name = %s"
        params.append(sel_genre)

    if sel_platform != "All":
        base_query += " AND vp.platform_name = %s"
        params.append(sel_platform)

    if sel_dev != "All":
        base_query += " AND vd.company_name = %s"
        params.append(sel_dev)

    if sel_pub != "All":
        base_query += " AND vp_pub.company_name = %s"
        params.append(sel_pub)

    # Group by is essential here because the JOINs might create duplicate rows for the same game
    base_query += " GROUP BY v.game_name, v.initial_release_date ORDER BY v.moby_score DESC LIMIT 100"

    results = run_query(base_query, tuple(params))
    st.dataframe(results, use_container_width=True)

# 5- TOP CHARTS
elif menu == "Top Charts":
    st.header("🏆 Top Charts")

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["By Genre", "By Year", "Top 5 MobyScore (Genre)", "Top 5 MobyScore (Setting)", "Top 5 Devs (Genre)"])

    # Top Games IN EACH Genre
    with tab1:
        st.subheader("Top Rated Games by Genre")

        # 1. Get list of genres for the dropdown
        genres_df = run_query("SELECT DISTINCT genre_name FROM Genre ORDER BY genre_name")
        target_genre = st.selectbox("Select a Genre:", genres_df['genre_name'].tolist())

        if target_genre:
            # 2. Get games for this genre
            query = """
                    SELECT v.game_name, v.critics_rating, v.players_rating, v.moby_score
                    FROM Video_game v
                             JOIN Video_game_genre g ON v.game_name = g.game_name AND v.initial_release_date = g.initial_release_date
                    WHERE g.genre_name = %s \
                    """
            genre_games = run_query(query, (target_genre,))

            if not genre_games.empty:
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("### 🏛️ Critics' Favorites")
                    # Sort by Critics Rating, filter out nulls, take top 10
                    top_critics = genre_games.dropna(subset=['critics_rating']).sort_values('critics_rating', ascending=False).head(10)
                    # Display specific columns
                    st.dataframe(top_critics[['game_name', 'critics_rating']], use_container_width=True, hide_index=True)

                with col2:
                    st.markdown("### 🎮 Players' Favorites")
                    # Sort by Players Rating, filter out nulls, take top 10
                    top_players = genre_games.dropna(subset=['players_rating']).sort_values('players_rating', ascending=False).head(10)
                    st.dataframe(top_players[['game_name', 'players_rating']], use_container_width=True, hide_index=True)
            else:
                st.warning("No games found for this genre.")

    # Top Games IN EACH Year
    with tab2:
        st.subheader("Top Rated Games by Year")

        # 1. Get list of years
        years_df = run_query("SELECT DISTINCT YEAR(initial_release_date) as yr FROM Video_game WHERE initial_release_date != '9999-12-31' ORDER BY yr DESC")
        target_year = st.selectbox("Select a Year:", years_df['yr'].tolist())

        if target_year:
            # 2. Get games for this year
            query = """
                    SELECT game_name, critics_rating, players_rating
                    FROM Video_game
                    WHERE YEAR(initial_release_date) = %s \
                    """
            year_games = run_query(query, (target_year,))

            if not year_games.empty:
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("### 🏛️ Critics' Choices")
                    top_critics = year_games.dropna(subset=['critics_rating']).sort_values('critics_rating', ascending=False).head(10)
                    st.dataframe(top_critics[['game_name', 'critics_rating']], use_container_width=True, hide_index=True)

                with col2:
                    st.markdown("### 🎮 Players' Choices")
                    top_players = year_games.dropna(subset=['players_rating']).sort_values('players_rating', ascending=False).head(10)
                    st.dataframe(top_players[['game_name', 'players_rating']], use_container_width=True, hide_index=True)
            else:
                st.warning("No games found for this year.")

    with tab3:
        st.subheader("Top 5 Games per Genre (Moby Score)")
        query = """
                SELECT g.genre_name, v.game_name, v.moby_score
                FROM Video_game v
                         JOIN Video_game_genre g ON v.game_name = g.game_name AND v.initial_release_date = g.initial_release_date
                WHERE v.moby_score IS NOT NULL \
                """
        df = run_query(query)
        if not df.empty:
            # Pandas code to get top 5 per genre
            top_5 = df.sort_values("moby_score", ascending=False).groupby("genre_name").head(5)
            st.dataframe(top_5.sort_values(["genre_name", "moby_score"], ascending=[True, False]), use_container_width=True)

    with tab4:
        st.subheader("Top 5 Games per Setting (Moby Score)")
        query = """
                SELECT s.setting_name, v.game_name, v.moby_score
                FROM Video_game v
                         JOIN Video_game_setting s ON v.game_name = s.game_name AND v.initial_release_date = s.initial_release_date
                WHERE v.moby_score IS NOT NULL \
                """
        df = run_query(query)
        if not df.empty:
            # Pandas code to get top 5 per setting
            top_5 = df.sort_values("moby_score", ascending=False).groupby("setting_name").head(5)
            st.dataframe(top_5.sort_values(["setting_name", "moby_score"], ascending=[True, False]), use_container_width=True)

    with tab5:
        st.subheader("Top 5 Development Companies per Genre (Critics Rating)")
        # We calculate the average critic rating for each company within each genre
        query = """
                SELECT g.genre_name, d.company_name, AVG(v.critics_rating) as avg_critic_rating
                FROM Video_game v
                         JOIN Video_game_developer d ON v.game_name = d.game_name AND v.initial_release_date = d.initial_release_date
                         JOIN Video_game_genre g ON v.game_name = g.game_name AND v.initial_release_date = g.initial_release_date
                WHERE v.critics_rating IS NOT NULL
                GROUP BY g.genre_name, d.company_name
                """
        df = run_query(query)
        if not df.empty:
            # Sort by rating, then take the top 5 companies for each genre
            top_5_devs = df.sort_values("avg_critic_rating", ascending=False).groupby("genre_name").head(5)

            # Display nicely formatted
            st.dataframe(
                top_5_devs.sort_values(["genre_name", "avg_critic_rating"], ascending=[True, False]),
                use_container_width=True
            )

# 6- DREAM GAME BUILDER
elif menu == "Dream Game Builder":
    st.header("✨ Dream Game Builder")
    st.markdown("Based on **Player Ratings**, here is the statistically 'Perfect' game spec:")


    def flexible_metric(label, value, delta):
        st.caption(label)  # Small label text
        st.markdown(f"#### {value}")  # Header text
        if delta:
            st.markdown(f":green[↑ {delta}]")  # Colored delta text
        else:
            st.write("") # Spacer


    st.markdown("### 🏭 Core Production Specs")
    col1, col2, col3, col4 = st.columns(4)

    # 1. Best Developer
    q_dev = """
            SELECT d.company_name, AVG(v.players_rating) as score
            FROM Video_game v JOIN Video_game_developer d ON v.game_name = d.game_name AND v.initial_release_date = d.initial_release_date
            WHERE v.players_rating IS NOT NULL GROUP BY d.company_name ORDER BY score DESC LIMIT 1 \
            """
    best_dev = run_query(q_dev)
    with col1:
        val = best_dev.iloc[0]['company_name'] if not best_dev.empty else "N/A"
        sc = f"{best_dev.iloc[0]['score']:.1f} Rating" if not best_dev.empty else None
        flexible_metric("Developer", val, sc)

    # 2. Best Publisher
    q_pub = """
            SELECT p.company_name, AVG(v.players_rating) as score
            FROM Video_game v JOIN Video_game_publisher p ON v.game_name = p.game_name AND v.initial_release_date = p.initial_release_date
            WHERE v.players_rating IS NOT NULL GROUP BY p.company_name ORDER BY score DESC LIMIT 1 \
            """
    best_pub = run_query(q_pub)
    with col2:
        val = best_pub.iloc[0]['company_name'] if not best_pub.empty else "N/A"
        sc = f"{best_pub.iloc[0]['score']:.1f} Rating" if not best_pub.empty else None
        flexible_metric("Publisher", val, sc)

    # 3. Best Genre
    q_gen = """
            SELECT g.genre_name, AVG(v.players_rating) as score
            FROM Video_game v JOIN Video_game_genre g ON v.game_name = g.game_name AND v.initial_release_date = g.initial_release_date
            WHERE v.players_rating IS NOT NULL GROUP BY g.genre_name ORDER BY score DESC LIMIT 1 \
            """
    best_gen = run_query(q_gen)
    with col3:
        val = best_gen.iloc[0]['genre_name'] if not best_gen.empty else "N/A"
        sc = f"{best_gen.iloc[0]['score']:.1f} Rating" if not best_gen.empty else None
        flexible_metric("Genre", val, sc)

    # 4. Best Setting
    q_set = """
            SELECT s.setting_name, AVG(v.players_rating) as score
            FROM Video_game v JOIN Video_game_setting s ON v.game_name = s.game_name AND v.initial_release_date = s.initial_release_date
            WHERE v.players_rating IS NOT NULL GROUP BY s.setting_name ORDER BY score DESC LIMIT 1 \
            """
    best_set = run_query(q_set)
    with col4:
        val = best_set.iloc[0]['setting_name'] if not best_set.empty else "N/A"
        sc = f"{best_set.iloc[0]['score']:.1f} Rating" if not best_set.empty else None
        flexible_metric("Setting", val, sc)

    st.divider() # Visual separator


    st.markdown("### 🎮 Gameplay & Design")
    col5, col6, col7, col8 = st.columns(4)

    # 5. Best Perspective
    q_pers = """
             SELECT p.perspective_name, AVG(v.players_rating) as score
             FROM Video_game v JOIN Video_game_perspective p ON v.game_name = p.game_name AND v.initial_release_date = p.initial_release_date
             WHERE v.players_rating IS NOT NULL GROUP BY p.perspective_name ORDER BY score DESC LIMIT 1 \
             """
    best_pers = run_query(q_pers)
    with col5:
        val = best_pers.iloc[0]['perspective_name'] if not best_pers.empty else "N/A"
        sc = f"{best_pers.iloc[0]['score']:.1f} Rating" if not best_pers.empty else None
        flexible_metric("Perspective", val, sc)

    # 6. Best Pacing
    q_pace = """
             SELECT p.pacing_name, AVG(v.players_rating) as score
             FROM Video_game v JOIN Video_game_pacing p ON v.game_name = p.game_name AND v.initial_release_date = p.initial_release_date
             WHERE v.players_rating IS NOT NULL GROUP BY p.pacing_name ORDER BY score DESC LIMIT 1 \
             """
    best_pace = run_query(q_pace)
    with col6:
        val = best_pace.iloc[0]['pacing_name'] if not best_pace.empty else "N/A"
        sc = f"{best_pace.iloc[0]['score']:.1f} Rating" if not best_pace.empty else None
        flexible_metric("Pacing", val, sc)

    # 7. Best Interface
    q_int = """
            SELECT i.interface, AVG(v.players_rating) as score
            FROM Video_game v JOIN Video_game_interface i ON v.game_name = i.game_name AND v.initial_release_date = i.initial_release_date
            WHERE v.players_rating IS NOT NULL GROUP BY i.interface ORDER BY score DESC LIMIT 1 \
            """
    best_int = run_query(q_int)
    with col7:
        val = best_int.iloc[0]['interface'] if not best_int.empty else "N/A"
        sc = f"{best_int.iloc[0]['score']:.1f} Rating" if not best_int.empty else None
        flexible_metric("Interface", val, sc)

    # 8. Best Input Device
    q_inp = """
            SELECT i.input_device_name, AVG(v.players_rating) as score
            FROM Video_game v JOIN Video_game_input_devices i ON v.game_name = i.game_name AND v.initial_release_date = i.initial_release_date
            WHERE v.players_rating IS NOT NULL GROUP BY i.input_device_name ORDER BY score DESC LIMIT 1 \
            """
    best_inp = run_query(q_inp)
    with col8:
        val = best_inp.iloc[0]['input_device_name'] if not best_inp.empty else "N/A"
        sc = f"{best_inp.iloc[0]['score']:.1f} Rating" if not best_inp.empty else None
        flexible_metric("Input Device", val, sc)

    st.divider()


    st.markdown("### 📦 Market & Format")
    col9, col10, col11, col12 = st.columns(4)

    # 9. Best Business Model
    q_biz = """
            SELECT b.business_model_name, AVG(v.players_rating) as score
            FROM Video_game v JOIN Video_game_business_model b ON v.game_name = b.game_name AND v.initial_release_date = b.initial_release_date
            WHERE v.players_rating IS NOT NULL GROUP BY b.business_model_name ORDER BY score DESC LIMIT 1 \
            """
    best_biz = run_query(q_biz)
    with col9:
        val = best_biz.iloc[0]['business_model_name'] if not best_biz.empty else "N/A"
        sc = f"{best_biz.iloc[0]['score']:.1f} Rating" if not best_biz.empty else None
        flexible_metric("Business Model", val, sc)

    # 10. Best Media Type
    q_med = """
            SELECT m.media_type_name, AVG(v.players_rating) as score
            FROM Video_game v JOIN Video_game_media_type m ON v.game_name = m.game_name AND v.initial_release_date = m.initial_release_date
            WHERE v.players_rating IS NOT NULL GROUP BY m.media_type_name ORDER BY score DESC LIMIT 1 \
            """
    best_med = run_query(q_med)
    with col10:
        val = best_med.iloc[0]['media_type_name'] if not best_med.empty else "N/A"
        sc = f"{best_med.iloc[0]['score']:.1f} Rating" if not best_med.empty else None
        flexible_metric("Media Type", val, sc)

    # 11. Best Maturity Rating
    q_mat = """
            SELECT m.maturity_rating, AVG(v.players_rating) as score
            FROM Video_game v JOIN Video_game_maturity_rating m ON v.game_name = m.game_name AND v.initial_release_date = m.initial_release_date
            WHERE v.players_rating IS NOT NULL GROUP BY m.maturity_rating ORDER BY score DESC LIMIT 1 \
            """
    best_mat = run_query(q_mat)
    with col11:
        val = best_mat.iloc[0]['maturity_rating'] if not best_mat.empty else "N/A"
        sc = f"{best_mat.iloc[0]['score']:.1f} Rating" if not best_mat.empty else None
        flexible_metric("Maturity Rating", val, sc)

    # 12. Conclusion
    with col12:
        st.write("") # Spacer
        st.success("If this game existed, it would be a masterpiece!")


# 7- DIRECTOR ANALYTICS
elif menu == "Director Analytics":
    st.header("🎬 Director Analytics")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Top 5 Most Prolific Directors")
        query = """
                SELECT director_name, COUNT(*) as game_count
                FROM Video_game
                WHERE director_name IS NOT NULL
                GROUP BY director_name
                ORDER BY game_count DESC
                    LIMIT 5 \
                """
        df = run_query(query)
        st.dataframe(df, use_container_width=True)

    with col2:
        st.subheader("Top 5 Collaborations (Director + Company)")
        # Join Director -> Game -> Developer
        query = """
                SELECT v.director_name, d.company_name, COUNT(*) as collab_count
                FROM Video_game v
                         JOIN Video_game_developer d ON v.game_name = d.game_name AND v.initial_release_date = d.initial_release_date
                WHERE v.director_name IS NOT NULL
                GROUP BY v.director_name, d.company_name
                ORDER BY collab_count DESC
                    LIMIT 5 \
                """
        df = run_query(query)
        st.dataframe(df, use_container_width=True)

# 8- PLATFORM STATS
elif menu == "Platform Stats":
    st.header("🕹️ Platform Statistics")

    query = """
            SELECT p.platform_name, COUNT(*) as game_count, AVG(v.critics_rating) as avg_critic, AVG(v.players_rating) as avg_player
            FROM Video_game v
                     JOIN Video_game_platform p ON v.game_name = p.game_name AND v.initial_release_date = p.initial_release_date
            GROUP BY p.platform_name
            ORDER BY game_count DESC \
            """
    df = run_query(query)

    # Interactive Bubble Chart
    if not df.empty:
        fig = px.scatter(df, x="avg_critic", y="avg_player",
                         size="game_count", color="platform_name",
                         hover_name="platform_name", size_max=60,
                         title="Platform Landscape: Quantity vs Quality")
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(df)