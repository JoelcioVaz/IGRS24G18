from twisted.internet import reactor
from twisted.internet.protocol import DatagramProtocol

domain = "acme.pt"
registered_users = {}  # Store registered users
kpi_metrics = {
   "Chamadas atendidas automaticamente": 0,
   "Conferências realizadas": 0,
}

class SIPServerProtocol(DatagramProtocol):
   def __init__(self):
       # Initialize pending_calls to track calls that need auto-answer
       self.pending_calls = {}

   def datagramReceived(self, data, addr):
       message = data.decode()
       print(f"Mensagem SIP recebida de {addr}: {message}")

       try:
           method, uri, headers, body = self.parse_sip_message(message)

           # Process SIP methods
           if method == "REGISTER":
               self.handle_register(headers, addr)
           elif method == "MESSAGE":
               self.handle_message(headers, body, addr)
           elif method == "INVITE":
               self.handle_invite(headers, addr)
           else:
               self.send_sip_response(501, "Not Implemented", addr, headers=headers)
       except Exception as e:
           print(f"Erro ao processar a mensagem SIP: {e}")

   def parse_sip_message(self, message):
       """Parse SIP message into method, URI, headers, and body"""
       lines = message.split("\r\n")
       method, uri, protocol = lines[0].split(" ")
       headers = {line.split(": ")[0]: line.split(": ")[1] for line in lines[1:] if ": " in line}
       body = lines[-1] if "\r\n\r\n" in message else ""
       return method, uri, headers, body

   def send_sip_response(self, code, reason, addr, headers=None, body=""):
       """Send a SIP response following RFC 3261"""
       response = f"SIP/2.0 {code} {reason}\r\n"

       if headers and "Via" in headers:
           response += f"Via: {headers['Via']}\r\n"
       if headers and "Call-ID" in headers:
           response += f"Call-ID: {headers['Call-ID']}\r\n"
       if headers and "CSeq" in headers:
           response += f"CSeq: {headers['CSeq']}\r\n"
       if headers and "From" in headers:
           response += f"From: {headers['From']}\r\n"
       if headers and "To" in headers:
           response += f"To: {headers['To']};tag=1234\r\n"

       # Include Contact header for successful responses
       if code == 200 and "From" in headers:
           response += f"Contact: {headers['From']}\r\n"

       response += f"Content-Length: {len(body)}\r\n\r\n{body}"
       print(f"Enviando resposta SIP para {addr}:\n{response}")
       self.transport.write(response.encode(), addr)

   def handle_register(self, headers, addr):
       """Handle SIP REGISTER"""
       aor = headers.get("From")
       contact = headers.get("Contact", "")
       expires = headers.get("Expires", "3600")  # Default to 3600 seconds if not specified

       # Validate domain
       if domain not in aor:
           self.send_sip_response(403, "Forbidden", addr, headers=headers)
           return

       # Check if it's a de-registration request
       if expires == "0":
           if aor in registered_users:
               del registered_users[aor]
               self.send_sip_response(200, "OK - De-registered", addr, headers=headers)
           else:
               self.send_sip_response(404, "Not Found", addr, headers=headers)
           return

       # Regular registration
       registered_users[aor] = {"status": "registered", "addr": addr, "contact": contact}
       self.send_sip_response(200, "OK - Registered", addr, headers=headers)

   def handle_invite(self, headers, addr):
       """Handle SIP INVITE (Forwarding INVITE to the called client)"""
       call_id = headers.get("Call-ID")
       to_uri = headers.get("To")
       from_uri = headers.get("From")

       print(f"Received INVITE for {to_uri} from {from_uri}")

       # Ensure the domain is valid
       if domain not in to_uri:
           self.send_sip_response(403, "Forbidden", addr, headers=headers)
           return

       if to_uri in registered_users:
           # Send 180 Ringing to the caller to indicate the call is ringing
           self.send_sip_response(180, "Ringing", addr, headers=headers)

           # Check if the called user is registered
           target_addr = registered_users[to_uri]["addr"]
           print(f"Forwarding INVITE to {target_addr}")
           
           # Forward the INVITE to the called client (Twinkle)
           self.transport.write(self.create_forwarded_invite(headers), target_addr)
           
           # Start a 30-second timer for automatic answering if no response
           self.pending_calls[call_id] = reactor.callLater(30, self.auto_answer_call, headers, addr)
       else:
           self.send_sip_response(404, "Not Found", addr, headers=headers)

   def create_forwarded_invite(self, headers):
       """Create a forwarded INVITE request to the target (called client)"""
       invite = f"INVITE {headers['To']} SIP/2.0\r\n"
       invite += f"Via: {headers['Via']}\r\n"
       invite += f"From: {headers['From']};tag=1234\r\n"
       invite += f"To: {headers['To']};tag=5678\r\n"  # Unique tag for called client
       invite += f"Call-ID: {headers['Call-ID']}\r\n"
       invite += f"CSeq: {headers['CSeq']}\r\n"
       invite += "Contact: <sip:server@acme.pt>\r\n"
       invite += "Content-Type: application/sdp\r\n"
       invite += "Content-Length: 0\r\n\r\n"
       return invite.encode()

   def auto_answer_call(self, headers, addr):
       """Automatically answer the call if no response received within 30 seconds"""
       print(f"No response from called client, answering automatically...")
       self.send_sip_response(200, "OK", addr, headers=headers)
       self.forward_200_ok_to_caller(headers, addr)

   def forward_200_ok_to_caller(self, headers, caller_addr):
       """Forward the 200 OK response from called client to the caller"""
       # Here, ensure to forward the response to the caller
       print(f"Forwarding 200 OK to caller {caller_addr}")
       self.send_sip_response(200, "OK", caller_addr, headers=headers)

# Start SIP server on UDP port 5060
reactor.listenUDP(5060, SIPServerProtocol(), interface="0.0.0.0")
print("Servidor SIP iniciado na porta UDP 5060")
reactor.run()