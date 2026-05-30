import time
import sys
from PyQt5.QtWidgets import QApplication
from sync_manager import SyncManager

def test():
    app = QApplication(sys.argv)
    
    # Create the sync manager
    manager = SyncManager(group_id="vu-mcq-sync-group-99", db_path="sync_queue_test.db")
    
    def on_connection(connected):
        print(f"Connection status: {connected}")
        if connected:
            print("Publishing fake job started event...")
            manager.publish_event('job_started', {
                'job_id': 'job_fake_pdf.pdf_12345',
                'pdf_name': 'fake_pdf.pdf'
            })
            
    def on_event(event):
        print(f"Received event from another user: {event}")
        
    manager.connection_status.connect(on_connection)
    manager.event_received.connect(on_event)
    
    # Run the event loop for 5 seconds to allow connection and publishing
    print("Testing sync manager. Waiting 5 seconds...")
    import threading
    def stop():
        time.sleep(5)
        app.quit()
    threading.Thread(target=stop).start()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    test()
