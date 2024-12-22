import sys
import KSR as KSR

# Dump Object Attributes (Unchanged)
def dumpObj(obj):           
    for attr in dir(obj):
        KSR.info("obj attr = %s" % attr)
        if (attr != "Status"):
            KSR.info(" type = %s\n" % type(getattr(obj, attr)))
        else:
            KSR.info("\n")
    return 1

# Initialization function
def mod_init():
    KSR.info("===== from Python mod init\n")
    return kamailio()

# Kamailio class with changes for the requirements
class kamailio:
    def __init__(self):
        KSR.info('===== kamailio.__init__\n')

    def child_init(self, rank):
        KSR.info('===== kamailio.child_init(%d)\n' % rank)
        return 0

    def ksr_request_route(self, msg):
        # Check if the user belongs to acme.pt domain
        to_uri = KSR.pv.get("$tu")  # Get the To URI
        if '@acme.pt' not in to_uri:
            KSR.info("Unauthorized domain: " + to_uri)
            KSR.sl.send_reply(403, "Forbidden")  # Reject with 403 Forbidden
            return 1

        if msg.Method == "REGISTER":
            # Only register users from acme.pt domain
            from_uri = KSR.pv.get("$fu")  # Get the From URI
            if '@acme.pt' in from_uri:
                KSR.info("REGISTER from: " + str(from_uri))
                KSR.registrar.save('location', 0)
                KSR.sl.send_reply(200, "OK")  # Successful registration
            else:
                KSR.sl.send_reply(403, "Forbidden")  # Reject non-acme.pt registrations
            return 1

        if msg.Method == "INVITE":
            # Check if the destination is a valid acme.pt user
            to_uri = KSR.pv.get("$tu")  # Get the To URI
            if '@acme.pt' in to_uri:
                KSR.info("INVITE R-URI: " + KSR.pv.get("$ru"))
                KSR.info("From: " + KSR.pv.get("$fu") + " To: " + KSR.pv.get("$tu"))
                
                # Check if the destination user is registered
                if KSR.registrar.lookup("location") == 1:
                    KSR.tm.t_relay()  # Forward the INVITE
                else:
                    KSR.sl.send_reply(404, "Not Found")  # User not registered
            else:
                # Reject if not an acme.pt user
                KSR.sl.send_reply(403, "Forbidden")
            return 1

        if msg.Method == "ACK":
            KSR.info("ACK R-URI: " + KSR.pv.get("$ru"))
            KSR.tm.t_relay()
            return 1

        if msg.Method == "CANCEL":
            KSR.info("CANCEL R-URI: " + KSR.pv.get("$ru"))
            KSR.tm.t_relay()
            return 1

        if msg.Method == "BYE":
            KSR.info("BYE R-URI: " + KSR.pv.get("$ru"))
            KSR.tm.t_relay()
            return 1

        if msg.Method == "MESSAGE":
            # Handle PIN verification via SIP MESSAGE
            to_uri = KSR.pv.get("$tu")  # Get the To URI
            if "validar@acme.pt" in to_uri:
                pin = KSR.pv.get("$body")
                if pin == "0000":
                    KSR.sl.send_reply(200, "OK")  # Correct PIN
                else:
                    KSR.sl.send_reply(401, "Unauthorized")  # Incorrect PIN
            return 1

    def ksr_reply_route(self, msg):
        KSR.info("===== response - from kamailio python script\n")
        KSR.info("Status is:" + str(KSR.pv.get("$rs")))
        return 1

    def ksr_onsend_route(self, msg):
        KSR.info("===== onsend route - from kamailio python script\n")
        KSR.info("      %s\n" % (msg.Type))
        return 1

    def ksr_onreply_route_INVITE(self, msg):
        KSR.info("===== INVITE onreply route - from kamailio python script\n")
        return 0

    def ksr_failure_route_INVITE(self, msg):
        KSR.info("===== INVITE failure route - from kamailio python script\n")
        return 1

    # Additional functions for call forwarding and conference handling

    def handle_forwarding(self, msg):
        # Handle re-routing based on the status of the recipient
        to_uri = KSR.pv.get("$tu")  # Get the To URI
        if '@acme.pt' in to_uri:
            # Check if the user is available, busy, or in conference
            if KSR.pv.get("$td") == "busy":
                KSR.info("Forwarding to busy announcement")
                KSR.pv.sets("$ru", "sip:busyann@127.0.0.1:5080")
            elif KSR.pv.get("$td") == "inconference":
                KSR.info("Forwarding to conference announcement")
                KSR.pv.sets("$ru", "sip:inconference@127.0.0.1:5080")
            else:
                KSR.info("Forwarding to registered user")
                KSR.tm.t_relay()  # Forward normally
            return 1
        else:
            KSR.sl.send_reply(403, "Forbidden")  # Not acme.pt domain
            return 1

    def ksr_conference(self, msg):
        # Handle conference room joining
        to_uri = KSR.pv.get("$tu")  # Get the To URI
        if "@acme.pt" in to_uri:
            KSR.pv.sets("$ru", "sip:conferencia@127.0.0.1:5090")
            KSR.tm.t_relay()  # Forward to conference server
        else:
            KSR.sl.send_reply(403, "Forbidden")  # Not acme.pt domain
        return 1
