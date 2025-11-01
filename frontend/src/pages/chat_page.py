from nicegui import ui
from datetime import datetime
from frontend.src.components.header import Header
from frontend.src.services.api_service import APIService

class ChatPage:
    def __init__(self, repo_id: str, auth_service):
        self.repo_id = repo_id
        self.auth_service = auth_service
        self.api_service = APIService(auth_service=auth_service)
        try:
            self.repository = self.api_service.get_repository(repo_id)
            # Auto-select first chat room
            chat_rooms = self.api_service.get_chat_rooms(repo_id)
            self.selected_chat_room = chat_rooms[0] if chat_rooms else None
        except Exception as e:
            self.repository = None
            self.selected_chat_room = None
            ui.notify(f"Failed to load repository data: {str(e)}", type='negative')
        self.message_input = None
        self.messages_container = None
        self.chat_area_container = None
        self.sidebar_container = None
        self.polling_timer = None
        self.polling_attempts = 0

    def render(self):
        if not self.repository:
            return self.render_not_found()

        # Main container - full viewport height
        with ui.element('div').style('height: 100vh; display: flex; flex-direction: column; overflow: hidden;'):
            # Header
            Header(self.auth_service).render()

            # Main content area
            with ui.element('div').style('flex: 1; display: flex; overflow: hidden;'):
                # Sidebar container
                self.sidebar_container = ui.element('div')
                with self.sidebar_container:
                    self.render_sidebar()

                # Chat area container
                self.chat_area_container = ui.element('div').style('flex: 1; display: flex; flex-direction: column; overflow: hidden;')
                with self.chat_area_container:
                    self.render_chat_area()

    def render_not_found(self):
        with ui.column().classes('w-full min-h-screen items-center justify-center'):
            ui.html('<h2 class="text-2xl font-bold text-gray-600">Repository Not Found</h2>')
            ui.button('Back to Repositories', on_click=lambda: ui.navigate.to('/repositories')).classes('rag-button-primary mt-4')

    def render_sidebar(self):
        try:
            chat_rooms = self.api_service.get_chat_rooms(self.repo_id)
        except Exception as e:
            ui.notify(f"Failed to load chat rooms: {str(e)}", type='negative')
            chat_rooms = []

        with ui.element('div').style('width: 280px; background-color: #f8fafc; border-right: 1px solid #e2e8f0; display: flex; flex-direction: column; overflow: hidden;'):
            # Header
            with ui.element('div').style('padding: 16px; border-bottom: 1px solid #e2e8f0;'):
                with ui.row().classes('items-center gap-3 mb-3'):
                    ui.html('<span style="color: #2563eb; font-size: 24px;">💬</span>')
                    ui.html('<h2 class="text-xl font-bold">Chat Rooms</h2>')

                with ui.element('div').style('width: 100%;'):
                    ui.button('➕ Add Chat', on_click=self.show_create_chat_dialog).classes('rag-button-primary').style('width: 100%;')

            # Chat rooms list
            with ui.element('div').style('flex: 1; overflow-y: auto; padding: 12px;'):
                for room in chat_rooms:
                    self.render_chat_room_item(room)

    def render_chat_room_item(self, room):
        is_selected = self.selected_chat_room and self.selected_chat_room["id"] == room["id"]
        room_id = room["id"]

        if is_selected:
            bg_color = "#dbeafe"
            border_color = "#3b82f6"
        else:
            bg_color = "white"
            border_color = "transparent"

        # Create a container for this specific room
        with ui.element('div').style(f'display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 12px; border-radius: 10px; background-color: {bg_color}; border: 2px solid {border_color}; margin-bottom: 6px; transition: all 0.2s; height: 52px; width: 100%;') as container:
            # Room name container - clickable
            with ui.element('div').style('flex: 1; min-width: 0; cursor: pointer;').on('click', lambda rid=room_id: self.handle_room_click_only(rid)):
                ui.html(f'<span style="font-weight: 500; font-size: 14px; color: #1f2937; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; display: block;">{room["name"]}</span>')

            # Options button (fixed position on right) - separate click handler
            with ui.element('div').style('flex-shrink: 0;'):
                ui.button('✕', on_click=lambda rid=room_id: self.handle_options_click_only(rid)).style('color: #6b7280; padding: 4px 8px; background: transparent; border: none; font-size: 18px; cursor: pointer; border-radius: 6px; min-width: 32px;').props('flat dense')

    def render_chat_area(self):
        with ui.element('div').style('flex: 1; display: flex; flex-direction: column; overflow: hidden;'):
            if not self.selected_chat_room:
                self.render_empty_chat_state()
            else:
                self.render_active_chat()

    def render_empty_chat_state(self):
        with ui.column().classes('flex-1 items-center justify-center p-8'):
            with ui.card().classes('rag-card text-center max-w-md'):
                ui.html('<div style="font-size: 96px; color: #60a5fa; margin-bottom: 16px;">💬</div>')
                ui.html('<h3 class="text-xl font-semibold text-gray-800 mb-2">Welcome to RAG Chat</h3>')
                ui.html(f'<p class="text-gray-600 mb-4">사이드바에서 채팅방을 생성하여 <strong>{self.repository["name"]}</strong> 레포지토리에 대한 대화를 시작하세요.</p>')
                ui.html('<p class="text-gray-500 text-sm mt-2">왼쪽 사이드바의 "➕ Add Chat" 버튼을 클릭하여 새로운 채팅방을 만들 수 있습니다.</p>')

    def render_active_chat(self):
        room = self.selected_chat_room

        with ui.element('div').style('flex: 1; display: flex; flex-direction: column; overflow: hidden;'):
            # Chat header - fixed height
            self.render_chat_header()

            # Messages area - flexible height with scroll
            with ui.element('div').style('flex: 1; overflow: hidden; display: flex; flex-direction: column;'):
                self.render_messages_area()

            # Input area - fixed height
            self.render_input_area()

        # 새로고침 후 로딩 상태 복원
        self.restore_loading_state_if_needed()

    def render_chat_header(self):
        room = self.selected_chat_room

        with ui.element('div').style('padding: 20px 24px; border-bottom: 1px solid #e5e7eb; background-color: white; display: flex; align-items: center; height: 80px;'):
            ui.html('<span style="color: #2563eb; font-size: 24px; margin-right: 12px;">💬</span>')
            with ui.column().classes('gap-1').style('flex: 1; min-width: 0;'):
                ui.html(f'<h3 style="font-weight: 600; font-size: 18px; color: #111827; margin: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{room["name"]}</h3>')
                ui.html(f'<p style="font-size: 13px; color: #6b7280; margin: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{self.repository["name"]} • {room["message_count"]} messages</p>')

    def render_messages_area(self):
        # Messages container - fixed size regardless of content
        with ui.element('div').style('flex: 1; overflow-y: auto; padding: 24px; background-color: #f9fafb; min-height: 0; width: 100%;').props('id=messages-container') as container:
            self.messages_container = container

            # Inner container for messages - centered with max width
            with ui.element('div').style('max-width: 1200px; margin: 0 auto; width: 100%; min-height: 100%; display: flex; flex-direction: column;'):
                try:
                    messages = self.api_service.get_messages(self.selected_chat_room["id"])
                except Exception as e:
                    ui.notify(f"Failed to load messages: {str(e)}", type='negative')
                    messages = []

                # Render messages with consistent spacing
                for i, message in enumerate(messages):
                    self.render_message(message)

    def render_message(self, message):
        import json

        is_user = message["sender_type"] == "user"

        # Parse sources if it's a JSON string
        sources = message.get("sources")
        if sources and isinstance(sources, str):
            try:
                sources = json.loads(sources)
            except:
                sources = None
        elif not sources:
            sources = None

        with ui.element('div').style('width: 100%; margin-bottom: 20px; display: flex; align-items: flex-start;'):
            if is_user:
                # User message - right aligned with fixed width
                ui.element('div').style('flex: 1; min-width: 0;')  # spacer
                with ui.element('div').style('width: 600px; max-width: 600px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 16px 18px; border-radius: 18px 18px 4px 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);'):
                    ui.html(f'<div style="white-space: pre-wrap; line-height: 1.5; word-break: break-word;">{message["content"]}</div>')
                    ui.html(f'<div style="font-size: 11px; opacity: 0.8; margin-top: 8px; text-align: right;">{message["created_at"].strftime("%H:%M")}</div>')
            else:
                # AI message - left aligned with fixed width
                with ui.element('div').style('width: 700px; max-width: 700px; background: white; border: 1px solid #e5e7eb; border-radius: 18px 18px 18px 4px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); overflow: hidden;'):

                    # AI Header with gradient
                    with ui.row().style('background: linear-gradient(90deg, #f8fafc 0%, #e2e8f0 100%); padding: 12px 16px; border-bottom: 1px solid #e5e7eb; align-items: center; gap: 8px;'):
                        ui.html('<div style="width: 28px; height: 28px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-size: 14px; font-weight: 600;">🤖</div>')
                        ui.html('<div style="font-weight: 600; color: #374151;">RAGIT</div>')
                        ui.html('<div style="background: linear-gradient(90deg, #10b981 0%, #059669 100%); color: white; padding: 2px 8px; border-radius: 12px; font-size: 10px; font-weight: 500;">AI + RAG</div>')
                        ui.element().style('flex: 1;')
                        ui.html(f'<div style="font-size: 11px; color: #6b7280;">{message["created_at"].strftime("%H:%M")}</div>')

                    # Message content
                    with ui.column().style('padding: 16px;'):
                        ui.html(f'<div style="white-space: pre-wrap; line-height: 1.6; color: #374151;">{message["content"]}</div>')

                        # Sources section with enhanced RAG styling
                        if sources:
                            with ui.column().style('margin-top: 16px; padding: 12px; background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%); border-radius: 8px; border-left: 4px solid #0ea5e9;'):
                                with ui.row().style('align-items: center; gap: 8px; margin-bottom: 8px;'):
                                    ui.html('<div style="width: 20px; height: 20px; background: linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%); border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-size: 10px;">📚</div>')
                                    ui.html('<div style="font-weight: 600; color: #0f172a; font-size: 13px;">Retrieved from Repository</div>')

                                with ui.column().style('gap: 6px;'):
                                    for i, source in enumerate(sources):
                                        # 새로운 형식 또는 기존 형식 모두 지원
                                        if isinstance(source, dict):
                                            # 새로운 형식 (딕셔너리)
                                            path = source.get('path', '')
                                            node_name = source.get('name', 'unknown')
                                            node_type = source.get('type', 'function')

                                            # 파일 경로와 라인 정보 추출
                                            parts = path.split(':')
                                            if len(parts) >= 2:
                                                file_path = parts[0]
                                                line_info = parts[1] if len(parts) > 1 else ""

                                                with ui.row().style('align-items: center; gap: 8px; padding: 6px 8px; background: rgba(255,255,255,0.7); border-radius: 6px; border: 1px solid rgba(14,165,233,0.2); cursor: pointer; transition: all 0.2s;').on('click', lambda fp=file_path, li=line_info, nn=node_name, nt=node_type: self.show_code_history_modal_with_node(fp, li, nn, nt)):
                                                    ui.html(f'<div style="width: 16px; height: 16px; background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); border-radius: 3px; display: flex; align-items: center; justify-content: center; color: white; font-size: 8px; font-weight: 600;">{i+1}</div>')
                                                    ui.html(f'<div style="font-size: 12px; color: #1e40af; font-family: monospace; text-decoration: underline;">{path} <span style="color: #6b7280;">({node_name})</span></div>')
                                                    ui.html('<div style="font-size: 10px; color: #6b7280; margin-left: auto;">📖 View History</div>')
                                            else:
                                                with ui.row().style('align-items: center; gap: 8px; padding: 6px 8px; background: rgba(255,255,255,0.7); border-radius: 6px; border: 1px solid rgba(14,165,233,0.2);'):
                                                    ui.html(f'<div style="width: 16px; height: 16px; background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); border-radius: 3px; display: flex; align-items: center; justify-content: center; color: white; font-size: 8px; font-weight: 600;">{i+1}</div>')
                                                    ui.html(f'<div style="font-size: 12px; color: #1e40af; font-family: monospace;">{path}</div>')
                                        else:
                                            # 기존 형식 (문자열)
                                            parts = source.split(':')
                                            if len(parts) >= 2:
                                                file_path = parts[0]
                                                line_info = parts[1] if len(parts) > 1 else ""

                                                with ui.row().style('align-items: center; gap: 8px; padding: 6px 8px; background: rgba(255,255,255,0.7); border-radius: 6px; border: 1px solid rgba(14,165,233,0.2); cursor: pointer; transition: all 0.2s;').on('click', lambda fp=file_path, li=line_info: self.show_code_history_modal(fp, li)):
                                                    ui.html(f'<div style="width: 16px; height: 16px; background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); border-radius: 3px; display: flex; align-items: center; justify-content: center; color: white; font-size: 8px; font-weight: 600;">{i+1}</div>')
                                                    ui.html(f'<div style="font-size: 12px; color: #1e40af; font-family: monospace; text-decoration: underline;">{source}</div>')
                                                    ui.html('<div style="font-size: 10px; color: #6b7280; margin-left: auto;">📖 View History</div>')
                                            else:
                                                with ui.row().style('align-items: center; gap: 8px; padding: 6px 8px; background: rgba(255,255,255,0.7); border-radius: 6px; border: 1px solid rgba(14,165,233,0.2);'):
                                                    ui.html(f'<div style="width: 16px; height: 16px; background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); border-radius: 3px; display: flex; align-items: center; justify-content: center; color: white; font-size: 8px; font-weight: 600;">{i+1}</div>')
                                                    ui.html(f'<div style="font-size: 12px; color: #1e40af; font-family: monospace;">{source}</div>')

                ui.element('div').style('flex: 1;')  # spacer

    def render_input_area(self):
        with ui.element('div').style('padding: 24px; border-top: 1px solid #e5e7eb; background-color: white;'):
            with ui.element('div').style('max-width: 1200px; margin: 0 auto; display: flex; gap: 16px; align-items: flex-end;'):
                # Text input
                self.message_input = ui.textarea(
                    placeholder=f'Ask anything about {self.repository["name"]}... (Press Enter to send, Shift+Enter for new line)'
                ).style('''
                    flex: 1;
                    min-height: 60px;
                    max-height: 200px;
                    padding: 16px 20px;
                    border: 2px solid #e2e8f0;
                    border-radius: 16px;
                    font-size: 15px;
                    line-height: 1.5;
                    resize: vertical;
                    font-family: system-ui, -apple-system, sans-serif;
                    transition: border-color 0.2s;
                ''').props('autofocus')

                # Add Enter key handling (Shift+Enter for newline)
                self.message_input.on('keydown.enter', lambda e: None if e.args.get('shiftKey') else self.send_message())

                # Send button
                ui.button('Send', icon='send', on_click=self.send_message).style('''
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 18px 36px;
                    border-radius: 12px;
                    border: none;
                    cursor: pointer;
                    font-size: 15px;
                    font-weight: 600;
                    min-width: 120px;
                    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.25);
                    transition: all 0.2s;
                ''').props('flat')


    def send_message(self):
        if not self.message_input.value.strip():
            return

        message_content = self.message_input.value.strip()
        self.message_input.value = ""

        try:
            # 1. 사용자 메시지 전송
            user_message = self.api_service.add_message(
                self.selected_chat_room["id"],
                "user",
                message_content
            )

            # 2. 사용자 메시지 렌더링
            self.refresh_messages()

            # 3. 로딩 메시지 표시
            self.show_bot_loading()

            # 4. 폴링 시작 (bot 응답 대기)
            self.start_polling_for_bot_response()

        except Exception as e:
            ui.notify(f"Failed to send message: {str(e)}", type='negative')

    def show_bot_loading(self):
        """Bot 응답 로딩 상태 표시"""
        with self.messages_container:
            # 로딩 메시지를 표시할 컨테이너
            with ui.element('div').style('width: 100%; margin-bottom: 20px; display: flex; align-items: flex-start;') as loading_container:
                loading_container.classes('bot-loading-message')

                with ui.element('div').style('width: 700px; max-width: 700px; background: white; border: 1px solid #e5e7eb; border-radius: 18px 18px 18px 4px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); overflow: hidden;'):
                    # AI Header
                    with ui.row().style('background: linear-gradient(90deg, #f8fafc 0%, #e2e8f0 100%); padding: 12px 16px; border-bottom: 1px solid #e5e7eb; align-items: center; gap: 8px;'):
                        ui.html('<div style="width: 28px; height: 28px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-size: 14px; font-weight: 600;">🤖</div>')
                        ui.html('<div style="font-weight: 600; color: #374151;">RAGIT</div>')
                        ui.html('<div style="background: linear-gradient(90deg, #10b981 0%, #059669 100%); color: white; padding: 2px 8px; border-radius: 12px; font-size: 10px; font-weight: 500;">AI + RAG</div>')

                    # 로딩 애니메이션
                    with ui.column().style('padding: 16px;'):
                        ui.html('''
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <div style="width: 8px; height: 8px; background: #667eea; border-radius: 50%; animation: pulse 1.5s ease-in-out infinite;"></div>
                                <div style="width: 8px; height: 8px; background: #667eea; border-radius: 50%; animation: pulse 1.5s ease-in-out 0.2s infinite;"></div>
                                <div style="width: 8px; height: 8px; background: #667eea; border-radius: 50%; animation: pulse 1.5s ease-in-out 0.4s infinite;"></div>
                                <span style="color: #6b7280; font-size: 14px; margin-left: 8px;">AI가 코드를 분석하고 응답을 생성하는 중...</span>
                            </div>
                            <style>
                                @keyframes pulse {
                                    0%, 100% { opacity: 0.3; transform: scale(0.8); }
                                    50% { opacity: 1; transform: scale(1.2); }
                                }
                            </style>
                        ''')

        # 스크롤을 최하단으로
        ui.run_javascript('''
            const container = document.getElementById('messages-container');
            if (container) {
                container.scrollTop = container.scrollHeight;
            }
        ''')

    def start_polling_for_bot_response(self):
        """Bot 응답을 주기적으로 폴링 (ui.timer 사용)"""
        self.polling_attempts = 0

        def check_bot_response():
            """타이머 콜백: Bot 응답 확인"""
            self.polling_attempts += 1

            try:
                # 새 메시지 확인
                messages = self.api_service.get_messages(self.selected_chat_room["id"])

                # 마지막 메시지가 bot 메시지인지 확인
                if messages and messages[-1]["sender_type"] == "bot":
                    # 폴링 중지
                    if self.polling_timer:
                        self.polling_timer.active = False
                        self.polling_timer = None

                    # 로딩 메시지 제거
                    ui.run_javascript('''
                        const loadingMessages = document.querySelectorAll('.bot-loading-message');
                        loadingMessages.forEach(msg => msg.remove());
                    ''')

                    # 채팅 영역 전체 다시 렌더링
                    self.chat_area_container.clear()
                    with self.chat_area_container:
                        self.render_chat_area()

                    return  # 폴링 종료

                # 최대 180초 (90회 * 2초) 후 타임아웃 - 긴 응답 대응
                if self.polling_attempts >= 90:
                    if self.polling_timer:
                        self.polling_timer.active = False
                        self.polling_timer = None

                    ui.run_javascript('''
                        const loadingMessages = document.querySelectorAll('.bot-loading-message');
                        loadingMessages.forEach(msg => msg.remove());
                    ''')
                    ui.notify("응답 생성 대기시간이 초과되었습니다 (3분). 잠시 후 새로고침해주세요.", type='warning')

            except Exception as e:
                print(f"Polling error: {e}")
                # 에러 발생 시 계속 폴링

        # 2초마다 실행되는 타이머 시작
        self.polling_timer = ui.timer(2.0, check_bot_response)

    def refresh_messages(self):
        """메시지 목록 새로고침"""
        self.messages_container.clear()

        with self.messages_container:
            # Inner container for messages
            with ui.element('div').style('max-width: 1200px; margin: 0 auto; width: 100%; min-height: 100%; display: flex; flex-direction: column;'):
                try:
                    messages = self.api_service.get_messages(self.selected_chat_room["id"])
                except Exception as e:
                    ui.notify(f"Failed to load messages: {str(e)}", type='negative')
                    messages = []

                # Render messages
                for message in messages:
                    self.render_message(message)

        # 스크롤을 최하단으로
        ui.run_javascript('''
            const container = document.getElementById('messages-container');
            if (container) {
                container.scrollTop = container.scrollHeight;
            }
        ''')


    def handle_room_click(self, e, room_id):
        """Handle room selection click"""
        # Find the room by id
        try:
            chat_rooms = self.api_service.get_chat_rooms(self.repo_id)
            room = next((r for r in chat_rooms if r["id"] == room_id), None)
            if room:
                self.select_chat_room(room)
        except Exception as ex:
            print(f"Error selecting room: {ex}")

    def handle_options_click(self, e, room_id):
        """Handle options button click"""
        # Stop event propagation to prevent room selection
        e.handled = True

        # Find the room by id
        try:
            chat_rooms = self.api_service.get_chat_rooms(self.repo_id)
            room = next((r for r in chat_rooms if r["id"] == room_id), None)
            if room:
                self.show_room_options(room, e)
        except Exception as ex:
            print(f"Error showing room options: {ex}")

    def handle_room_click_only(self, room_id):
        """Handle room name click to select room (no event object)"""
        try:
            chat_rooms = self.api_service.get_chat_rooms(self.repo_id)
            room = next((r for r in chat_rooms if r["id"] == room_id), None)
            if room:
                self.select_chat_room(room)
        except Exception as ex:
            print(f"Error selecting room: {ex}")

    def handle_options_click_only(self, room_id):
        """Handle options button click to show modal (no event object)"""
        try:
            chat_rooms = self.api_service.get_chat_rooms(self.repo_id)
            room = next((r for r in chat_rooms if r["id"] == room_id), None)
            if room:
                self.show_room_options(room, None)
        except Exception as ex:
            print(f"Error showing options: {ex}")

    def select_chat_room(self, room):
        self.selected_chat_room = room

        # Update the sidebar to show correct selection
        self.sidebar_container.clear()
        with self.sidebar_container:
            self.render_sidebar()

        # Update the chat area
        self.chat_area_container.clear()
        with self.chat_area_container:
            self.render_chat_area()

        ui.update()

    def show_create_chat_dialog(self):
        with ui.dialog() as dialog, ui.card().classes('w-96'):
            ui.html('<h3 class="text-lg font-semibold mb-4">Create New Chat Room</h3>')

            with ui.column().classes('gap-4'):
                name_input = ui.input('Room Name', placeholder='e.g., Feature Discussion').classes('rag-input w-full')

                with ui.row().classes('gap-2 mt-4'):
                    ui.button('Cancel', on_click=dialog.close).classes('rag-button-secondary')
                    ui.button('Create Room', on_click=lambda: self.create_chat_room(name_input.value, dialog)).classes('rag-button-primary')

        dialog.open()

    def create_chat_room(self, name, dialog):
        if not name.strip():
            ui.notify('Please enter a room name', color='red')
            return

        try:
            new_room = self.api_service.create_chat_room(name.strip(), self.repo_id)
        except Exception as e:
            ui.notify(f"Failed to create chat room: {str(e)}", type='negative')
            return

        ui.notify(f'Chat room "{name}" created successfully!', color='green')
        dialog.close()

        # 새로 생성된 채팅방 자동 선택 및 UI 업데이트
        self.selected_chat_room = new_room

        # Update the sidebar to show new room
        self.sidebar_container.clear()
        with self.sidebar_container:
            self.render_sidebar()

        # Update the chat area to show new room
        self.chat_area_container.clear()
        with self.chat_area_container:
            self.render_chat_area()

        ui.update()

    def show_room_options(self, room, event):
        # Stop event propagation to prevent room selection
        if event:
            event.stop_propagation = True

        with ui.dialog() as dialog, ui.card().style('width: 320px; padding: 24px;'):
            ui.html(f'<h3 style="font-size: 18px; font-weight: 600; margin-bottom: 20px; color: #111827;">{room["name"]}</h3>')

            ui.button('🗑️ Delete Room', on_click=lambda: self.delete_room(room, dialog)).style('''
                background: #fef2f2;
                color: #dc2626;
                padding: 12px 20px;
                border-radius: 8px;
                width: 100%;
                border: 1px solid #fecaca;
                cursor: pointer;
                font-weight: 500;
                font-size: 14px;
            ''')

            ui.button('Cancel', on_click=dialog.close).style('''
                background: #f3f4f6;
                color: #374151;
                padding: 12px 20px;
                border-radius: 8px;
                width: 100%;
                border: none;
                cursor: pointer;
                font-weight: 500;
                font-size: 14px;
                margin-top: 8px;
            ''')

        dialog.open()

    def delete_room(self, room, dialog):
        ui.notify('Room deletion is not available in demo mode', color='blue')
        dialog.close()

    def restore_loading_state_if_needed(self):
        """새로고침 후 로딩 상태 복원 (마지막 메시지가 user이고 bot 응답 대기 중인 경우)"""
        try:
            messages = self.api_service.get_messages(self.selected_chat_room["id"])

            # 메시지가 있고, 마지막 메시지가 user인 경우
            if messages and messages[-1]["sender_type"] == "user":
                # Bot 응답이 아직 없으므로 로딩 표시 + 폴링 시작
                # 약간의 지연을 두고 실행 (UI 렌더링 완료 후)
                ui.timer(0.1, lambda: self._restore_loading_delayed(), once=True)

        except Exception as e:
            print(f"Failed to restore loading state: {e}")

    def _restore_loading_delayed(self):
        """로딩 상태 복원 (지연 실행)"""
        self.show_bot_loading()
        self.start_polling_for_bot_response()

    def show_code_history_modal_with_node(self, file_path: str, line_info: str, node_name: str, node_type: str):
        """코드 히스토리 모달 창 표시 (노드 이름 포함)"""
        from nicegui import ui
        import asyncio

        # 모달 다이얼로그 생성
        with ui.dialog() as dialog, ui.card().style('width: 90%; max-width: 1200px; height: 80vh; display: flex; flex-direction: column;'):
            # 모달 헤더
            with ui.row().style('justify-content: space-between; align-items: center; padding: 16px; border-bottom: 1px solid #e5e7eb; background: linear-gradient(90deg, #f8fafc 0%, #e2e8f0 100%);'):
                with ui.row().style('align-items: center; gap: 12px;'):
                    ui.html('<div style="font-size: 24px;">📖</div>')
                    ui.html(f'<h3 style="margin: 0; font-size: 18px; font-weight: 600;">Code History: {file_path}</h3>')
                ui.button(icon='close', on_click=dialog.close).props('flat')

            # 로딩 상태
            loading_container = ui.column().style('flex: 1; align-items: center; justify-content: center; padding: 24px;')
            with loading_container:
                ui.spinner(size='lg')
                ui.html('<p style="margin-top: 16px; color: #6b7280;">Loading history...</p>')

            # 비동기로 히스토리 데이터 로드
            async def load_history():
                try:
                    # node_name이 이미 있으므로 직접 전달
                    response = await self.api_service.get_code_history(
                        self.repo_id,
                        file_path,
                        node_name=node_name,
                        node_type=node_type
                    )

                    # 로딩 컨테이너 제거
                    loading_container.clear()

                    if response.get('success'):
                        history = response.get('history', [])
                        # response에서 실제 node_name과 node_type 가져오기
                        actual_node_name = response.get('node_name', node_name)
                        actual_node_type = response.get('node_type', node_type)

                        if history:
                            # 히스토리 컨텐츠 표시
                            with loading_container:
                                # 스크롤 가능한 컨테이너
                                with ui.element('div').style('width: 100%; height: 100%; overflow-y: auto; padding: 16px;'):
                                    ui.html(f'<p style="color: #374151; margin-bottom: 16px;">Found <strong>{len(history)}</strong> changes for {actual_node_type} <code>{actual_node_name}</code></p>')

                                    # 각 변경사항 표시
                                    for change in history:
                                        with ui.card().style('margin-bottom: 16px; border: 1px solid #e5e7eb;'):
                                            # 커밋 정보 헤더
                                            with ui.row().style('padding: 12px; background: #f9fafb; border-bottom: 1px solid #e5e7eb; align-items: center; gap: 16px;'):
                                                ui.html(f'<div style="background: #3b82f6; color: white; padding: 4px 8px; border-radius: 4px; font-family: monospace; font-size: 12px;">{change["commit_hash"]}</div>')
                                                with ui.column().style('flex: 1;'):
                                                    ui.html(f'<div style="font-weight: 600; color: #111827;">{change["commit_message"]}</div>')
                                                    ui.html(f'<div style="font-size: 12px; color: #6b7280;">by {change["author"]} • {change["date"]}</div>')

                                            # Diff 표시
                                            if change.get('highlighted_diff'):
                                                with ui.element('div').style('padding: 12px; background: #f9fafb;'):
                                                    ui.html('<div style="font-size: 12px; font-weight: 600; color: #374151; margin-bottom: 8px;">Changes:</div>')
                                                    with ui.element('pre').style('background: #1f2937; color: #f3f4f6; padding: 12px; border-radius: 4px; font-family: monospace; font-size: 12px; overflow-x: auto; margin: 0;'):
                                                        # Diff를 HTML로 변환
                                                        diff_html = self._format_diff_as_html(change['highlighted_diff'])
                                                        ui.html(diff_html)
                        else:
                            # 히스토리가 없는 경우
                            with loading_container:
                                ui.html('<div style="text-align: center; padding: 48px;">')
                                ui.html('<div style="font-size: 48px; color: #9ca3af; margin-bottom: 16px;">📭</div>')
                                ui.html('<p style="color: #6b7280;">No history found for this code segment.</p>')
                                ui.html('</div>')
                    else:
                        # 에러 처리
                        with loading_container:
                            ui.html('<div style="text-align: center; padding: 48px;">')
                            ui.html('<div style="font-size: 48px; color: #ef4444; margin-bottom: 16px;">❌</div>')
                            ui.html(f'<p style="color: #dc2626;">Failed to load history: {response.get("error", "Unknown error")}</p>')
                            ui.html('</div>')

                except Exception as e:
                    # 예외 처리
                    loading_container.clear()
                    with loading_container:
                        ui.html('<div style="text-align: center; padding: 48px;">')
                        ui.html('<div style="font-size: 48px; color: #ef4444; margin-bottom: 16px;">⚠️</div>')
                        ui.html(f'<p style="color: #dc2626;">An error occurred: {str(e)}</p>')
                        ui.html('</div>')

            # 비동기 작업 실행
            asyncio.create_task(load_history())

        # 모달 열기
        dialog.open()

    def show_code_history_modal(self, file_path: str, line_info: str):
        """코드 히스토리 모달 창 표시"""
        from nicegui import ui
        import asyncio

        # 모달 다이얼로그 생성
        with ui.dialog() as dialog, ui.card().style('width: 90%; max-width: 1200px; height: 80vh; display: flex; flex-direction: column;'):
            # 모달 헤더
            with ui.row().style('justify-content: space-between; align-items: center; padding: 16px; border-bottom: 1px solid #e5e7eb; background: linear-gradient(90deg, #f8fafc 0%, #e2e8f0 100%);'):
                with ui.row().style('align-items: center; gap: 12px;'):
                    ui.html('<div style="font-size: 24px;">📖</div>')
                    ui.html(f'<h3 style="margin: 0; font-size: 18px; font-weight: 600;">Code History: {file_path}</h3>')
                ui.button(icon='close', on_click=dialog.close).props('flat')

            # 로딩 상태
            loading_container = ui.column().style('flex: 1; align-items: center; justify-content: center; padding: 24px;')
            with loading_container:
                ui.spinner(size='lg')
                ui.html('<p style="margin-top: 16px; color: #6b7280;">Loading history...</p>')

            # 비동기로 히스토리 데이터 로드
            async def load_history():
                try:
                    # Backend API가 line_info를 받아서 자동으로 node_name을 찾도록 함
                    # API 호출 (line_info 전달)
                    response = await self.api_service.get_code_history(
                        self.repo_id,
                        file_path,
                        line_info=line_info  # line_info 전달
                    )

                    # 로딩 컨테이너 제거
                    loading_container.clear()

                    if response.get('success'):
                        history = response.get('history', [])
                        # response에서 실제 node_name과 node_type 가져오기
                        actual_node_name = response.get('node_name', 'unknown')
                        actual_node_type = response.get('node_type', 'function')

                        if history:
                            # 히스토리 컨텐츠 표시
                            with loading_container:
                                # 스크롤 가능한 컨테이너
                                with ui.element('div').style('width: 100%; height: 100%; overflow-y: auto; padding: 16px;'):
                                    ui.html(f'<p style="color: #374151; margin-bottom: 16px;">Found <strong>{len(history)}</strong> changes for {actual_node_type} <code>{actual_node_name}</code></p>')

                                    # 각 변경사항 표시
                                    for change in history:
                                        with ui.card().style('margin-bottom: 16px; border: 1px solid #e5e7eb;'):
                                            # 커밋 정보 헤더
                                            with ui.row().style('padding: 12px; background: #f9fafb; border-bottom: 1px solid #e5e7eb; align-items: center; gap: 16px;'):
                                                ui.html(f'<div style="background: #3b82f6; color: white; padding: 4px 8px; border-radius: 4px; font-family: monospace; font-size: 12px;">{change["commit_hash"]}</div>')
                                                with ui.column().style('flex: 1;'):
                                                    ui.html(f'<div style="font-weight: 600; color: #111827;">{change["commit_message"]}</div>')
                                                    ui.html(f'<div style="font-size: 12px; color: #6b7280;">by {change["author"]} • {change["date"]}</div>')

                                            # Diff 표시
                                            if change.get('highlighted_diff'):
                                                with ui.element('div').style('padding: 12px; background: #f9fafb;'):
                                                    ui.html('<div style="font-size: 12px; font-weight: 600; color: #374151; margin-bottom: 8px;">Changes:</div>')
                                                    with ui.element('pre').style('background: #1f2937; color: #f3f4f6; padding: 12px; border-radius: 4px; font-family: monospace; font-size: 12px; overflow-x: auto; margin: 0;'):
                                                        # Diff를 HTML로 변환
                                                        diff_html = self._format_diff_as_html(change['highlighted_diff'])
                                                        ui.html(diff_html)
                        else:
                            # 히스토리가 없는 경우
                            with loading_container:
                                ui.html('<div style="text-align: center; padding: 48px;">')
                                ui.html('<div style="font-size: 48px; color: #9ca3af; margin-bottom: 16px;">📭</div>')
                                ui.html('<p style="color: #6b7280;">No history found for this code segment.</p>')
                                ui.html('</div>')
                    else:
                        # 에러 처리
                        with loading_container:
                            ui.html('<div style="text-align: center; padding: 48px;">')
                            ui.html('<div style="font-size: 48px; color: #ef4444; margin-bottom: 16px;">❌</div>')
                            ui.html(f'<p style="color: #dc2626;">Failed to load history: {response.get("error", "Unknown error")}</p>')
                            ui.html('</div>')

                except Exception as e:
                    # 예외 처리
                    loading_container.clear()
                    with loading_container:
                        ui.html('<div style="text-align: center; padding: 48px;">')
                        ui.html('<div style="font-size: 48px; color: #ef4444; margin-bottom: 16px;">⚠️</div>')
                        ui.html(f'<p style="color: #dc2626;">An error occurred: {str(e)}</p>')
                        ui.html('</div>')

            # 비동기 작업 실행
            asyncio.create_task(load_history())

        # 모달 열기
        dialog.open()

    def _format_diff_as_html(self, diff_text: str) -> str:
        """Diff 텍스트를 HTML로 포맷팅"""
        lines = diff_text.split('\n')
        formatted_lines = []

        for line in lines:
            if line.startswith('+'):
                formatted_lines.append(f'<span style="color: #10b981;">+ {line[1:]}</span>')
            elif line.startswith('-'):
                formatted_lines.append(f'<span style="color: #ef4444;">- {line[1:]}</span>')
            else:
                formatted_lines.append(f'<span style="color: #9ca3af;">{line}</span>')

        return '<br>'.join(formatted_lines)