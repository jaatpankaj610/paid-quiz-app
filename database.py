import sqlite3

conn = sqlite3.connect("quiz.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    score INTEGER DEFAULT 0,
    total INTEGER DEFAULT 0
)
""")

conn.commit()


def add_user(user_id, username):

    cursor.execute(
        "INSERT OR IGNORE INTO users(user_id,username,score,total) VALUES(?,?,0,0)",
        (user_id, username)
    )

    conn.commit()


def update_score(user_id, correct):

    cursor.execute(
        "SELECT score,total FROM users WHERE user_id=?",
        (user_id,)
    )

    row = cursor.fetchone()

    if row:

        score, total = row

        total += 1

        if correct:
            score += 1

        cursor.execute(
            "UPDATE users SET score=?,total=? WHERE user_id=?",
            (score, total, user_id)
        )

        conn.commit()


def get_score(user_id):

    cursor.execute(
        "SELECT score,total FROM users WHERE user_id=?",
        (user_id,)
    )

    row = cursor.fetchone()

    if row:
        return row

    return (0, 0)


def leaderboard():

    cursor.execute("""
    SELECT username,score,total
    FROM users
    ORDER BY score DESC
    LIMIT 10
    """)

    return cursor.fetchall()
