Descrição Geral
Este código implementa funcionalidades de manipulação de mensagens SIP (Session Initiation Protocol) em um script Python para o Kamailio, um servidor SIP de alta performance. O script define regras e rotas de processamento de mensagens SIP, como registro de usuários, encaminhamento de chamadas, conferências e mensagens SIP.

O módulo utiliza a API Python do Kamailio (referenciada como KSR) para interagir com a pilha SIP. A lógica é personalizada para suportar o domínio acme.pt, permitindo apenas interações de usuários pertencentes a este domínio.

Estrutura do Código
1. Função dumpObj
Utilizada para inspecionar e exibir atributos de um objeto.
Objetivo principal: auxiliar no desenvolvimento e debugging, exibindo os atributos de um objeto SIP recebido.
2. Função mod_init
Inicializa o módulo Kamailio e retorna uma instância da classe kamailio.
É chamada automaticamente quando o script é carregado no Kamailio.
3. Classe kamailio
A classe central que define o comportamento SIP. Seus métodos tratam as mensagens SIP recebidas e gerenciam diferentes cenários.

Métodos Específicos
__init__

Executado quando a classe é inicializada.
Utilizado para logging e configurações iniciais.
child_init

Chamado durante a inicialização de processos filho do Kamailio.
Faz logging do rank do processo filho.
ksr_request_route

Rota principal para lidar com mensagens SIP recebidas.
Comportamento baseado no método SIP (REGISTER, INVITE, etc.).
Casos Implementados:

REGISTER:
Permite apenas registros de usuários com o domínio @acme.pt.
Responde com 200 OK em caso de sucesso ou 403 Forbidden caso contrário.
INVITE:
Verifica se o destinatário pertence ao domínio acme.pt.
Encaminha a chamada (t_relay) se o usuário estiver registrado; caso contrário, responde com 404 Not Found.
ACK, CANCEL, BYE:
Encaminha diretamente estas mensagens utilizando t_relay.
MESSAGE:
Implementa verificação de PIN através de mensagens SIP para o endereço validar@acme.pt.
Responde com 200 OK se o PIN for correto (0000) ou 401 Unauthorized se estiver incorreto.
ksr_reply_route

Gerencia respostas SIP enviadas pelo servidor.
Faz logging do status da resposta.
ksr_onsend_route

Rota para mensagens enviadas pelo servidor.
Faz logging do tipo da mensagem.
ksr_onreply_route_INVITE e ksr_failure_route_INVITE

Rota para lidar com respostas ou falhas específicas do método INVITE.
4. Funcionalidades Adicionais
Encaminhamento de Chamadas
Método handle_forwarding:
Lida com diferentes estados do destinatário (busy, inconference, ou disponível).
Encaminha chamadas para anúncios específicos ou diretamente para o usuário registrado.
Conferências
Método ksr_conference:
Gerencia o encaminhamento de mensagens SIP destinadas à sala de conferência do domínio acme.pt.
Encaminha para sip:conferencia@127.0.0.1:5080.
Fluxo SIP no Código
Recepção da Mensagem SIP

A mensagem SIP é analisada e processada no método ksr_request_route.
Verificação do Método SIP

Cada método (REGISTER, INVITE, etc.) tem uma lógica específica para processamento.
Encaminhamento ou Resposta

Com base na lógica do método, as mensagens podem ser:
Encaminhadas: Utilizando t_relay.
Respondidas: Com códigos apropriados (200 OK, 403 Forbidden, etc.).
Gestão de Estados Específicos

Lógica personalizada para cenários como PIN verification e conferências.
Conformidade com os Requisitos
Domínio acme.pt: Apenas mensagens de/para este domínio são processadas.
Manuseio de Mensagens SIP: Implementação robusta de métodos como REGISTER, INVITE, e MESSAGE.
Encaminhamento Condicional: Suporte para estados como "busy" e "inconference".
Verificação de PIN: Lógica dedicada para validação de mensagens MESSAGE.

Para Rodar o script é necessário usar a maquina virtual xbuntu23. Dentro na maquina virtual rodar o ficheiro app-a.cfg na directoria /igrstools/kamailio/app-a.cfg , no penultimo comando  substituir o .py pelo script.
Depois na linha de comando dentro da directoria , rodar o comando sudo kamailio -f app-a.cfg -E -D 2
