import json
import sqlite3
import threading
import time
import uuid
import paho.mqtt.client as mqtt
from PyQt5.QtCore import QObject, pyqtSignal

class SyncManager(QObject):
    # Signals to communicate with the UI
    event_received = pyqtSignal(dict)
    connection_status = pyqtSignal(bool)

    def __init__(self, group_id="vu-mcq-sync-group-99", db_path="sync_queue.db"):
        super().__init__()
        self.group_id = group_id
        self.topic = f"vuedu/sync/{self.group_id}"
        self.db_path = db_path
        self.client_id = f"client_{uuid.uuid4().hex[:8]}"
        
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=self.client_id)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        
        self.connected = False
        
        self._init_db()
        self._connect_mqtt()

    def _init_db(self):
        """Initialize SQLite for offline queue."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS sync_events (
                    id TEXT PRIMARY KEY,
                    event_type TEXT,
                    payload TEXT,
                    status TEXT,
                    timestamp REAL
                )
            ''')
            conn.commit()

    def _connect_mqtt(self):
        """Connect to public MQTT broker in a background thread."""
        def run():
            try:
                # Using a reliable free public broker
                self.client.connect("broker.hivemq.com", 1883, 60)
                self.client.loop_start()
            except Exception as e:
                print(f"MQTT Connect Error: {e}")
                
        threading.Thread(target=run, daemon=True).start()

    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            print(f"Connected to sync server! Subscribing to {self.topic}")
            self.connected = True
            self.connection_status.emit(True)
            self.client.subscribe(self.topic)
            self.sync_offline_events()
        else:
            print(f"Failed to connect, return code {reason_code}")

    def on_disconnect(self, client, userdata, flags, reason_code, properties):
        print("Disconnected from sync server.")
        self.connected = False
        self.connection_status.emit(False)

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            # Ignore messages sent by ourselves
            if payload.get("client_id") == self.client_id:
                return
                
            self.event_received.emit(payload)
        except Exception as e:
            print(f"Error parsing incoming sync message: {e}")

    def sync_offline_events(self):
        """Sync any pending events when connection is restored."""
        if not self.connected:
            return
            
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, event_type, payload FROM sync_events WHERE status='pending' ORDER BY timestamp ASC")
            rows = cursor.fetchall()
            
            for row in rows:
                event_id, event_type, payload_str = row
                try:
                    payload = json.loads(payload_str)
                    
                    # Wrap with metadata
                    message = {
                        "client_id": self.client_id,
                        "event_id": event_id,
                        "event_type": event_type,
                        "payload": payload,
                        "timestamp": time.time()
                    }
                    
                    self.client.publish(self.topic, json.dumps(message), qos=1)
                    
                    # Mark as synced
                    cursor.execute("UPDATE sync_events SET status='synced' WHERE id=?", (event_id,))
                except Exception as e:
                    print(f"Error syncing event {event_id}: {e}")
                    
            conn.commit()

    def publish_event(self, event_type, payload):
        """Publish a new event to the group."""
        event_id = str(uuid.uuid4())
        payload_str = json.dumps(payload)
        
        # 1. Save to SQLite as pending (offline queue)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO sync_events (id, event_type, payload, status, timestamp) VALUES (?, ?, ?, ?, ?)",
                (event_id, event_type, payload_str, "pending", time.time())
            )
            conn.commit()
            
        # 2. Try to sync immediately
        self.sync_offline_events()
