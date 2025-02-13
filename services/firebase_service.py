import firebase_admin
from firebase_admin import credentials, firestore
import json
from config import FIREBASE_CREDENTIALS

# Initialize Firebase
cred = credentials.Certificate(json.loads(FIREBASE_CREDENTIALS))
firebase_admin.initialize_app(cred)
db = firestore.client()

async def store_user_query(user_id: int, command: str, query: str):
    """Store user query in Firebase."""
    try:
        doc_ref = db.collection('queries').document()
        doc_ref.set({
            'user_id': user_id,
            'command': command,
            'query': query,
            'timestamp': firestore.SERVER_TIMESTAMP
        })
    except Exception as e:
        print(f"Failed to store query: {str(e)}")

async def get_user_stats(user_id: int):
    """Get user statistics from Firebase."""
    try:
        queries = db.collection('queries').where('user_id', '==', user_id).stream()
        return len(list(queries))
    except Exception as e:
        print(f"Failed to get user stats: {str(e)}")
        return 0
