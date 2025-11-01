from nicegui import ui
from frontend.src.components.header import Header
from frontend.src.services.api_service import APIService

class RepositorySettingsPage:
    def __init__(self, auth_service, selected_repo_id: str = None):
        self.auth_service = auth_service
        self.api_service = APIService(auth_service=auth_service)
        self.repo_containers = {}  # UI 컨테이너들을 저장할 딕셔너리
        try:
            repositories = self.api_service.get_repositories()

            # URL 파라미터로 전달된 repo_id가 있으면 해당 repository 선택
            if selected_repo_id:
                self.selected_repo = next((repo for repo in repositories if str(repo["id"]) == selected_repo_id), None)
                # 못 찾으면 첫 번째 선택
                if not self.selected_repo:
                    self.selected_repo = repositories[0] if repositories else None
            else:
                self.selected_repo = repositories[0] if repositories else None
        except Exception as e:
            ui.notify(f"Failed to load repositories: {str(e)}", type='negative')
            self.selected_repo = None

    def render(self):
        with ui.column().style('width: 100%; min-height: 100vh; margin: 0; padding: 0;'):
            Header(self.auth_service).render()

            with ui.row().style('width: 100%; height: calc(100vh - 60px); margin: 0; padding: 0;'):
                self.render_sidebar()
                self.render_main_content()

    def render_sidebar(self):
        with ui.column().style('width: 320px; height: 100%; background-color: #f8fafc; border-right: 1px solid #e2e8f0; padding: 24px; overflow-y: auto;'):
            ui.html('<h2 style="font-size: 20px; font-weight: 600; margin-bottom: 16px;">Repositories</h2>')

            if self.auth_service.is_admin():
                ui.button('➕ Add New Repository', on_click=self.show_add_repository_dialog).style('width: 100%; background-color: #3b82f6; color: white; padding: 8px 16px; border-radius: 6px; border: none; margin-bottom: 16px;')

            try:
                repositories = self.api_service.get_repositories()
            except Exception as e:
                ui.notify(f"Failed to load repositories: {str(e)}", type='negative')
                repositories = []

            for repo in repositories:
                # 디버깅: 에러 상태 레포지토리 로깅
                if repo.get("status") == "error":
                    print(f"[DEBUG] Error repository: {repo.get('name')}")
                    print(f"[DEBUG] Error message: {repo.get('error_message')}")
                    print(f"[DEBUG] Full repo data: {repo}")
                self.render_repository_item(repo)

    def render_repository_item(self, repo):
        is_selected = self.selected_repo and self.selected_repo["id"] == repo["id"]

        if is_selected:
            item_style = 'width: 100%; padding: 12px; margin-bottom: 8px; border-radius: 8px; cursor: pointer; border: 2px solid #3b82f6; background-color: #dbeafe;'
        else:
            item_style = 'width: 100%; padding: 12px; margin-bottom: 8px; border-radius: 8px; cursor: pointer; border: 1px solid #e5e7eb; background-color: white;'

        # Create a container that will be refreshed when selection changes
        container = ui.column().style(item_style).on('click', lambda r=repo: self.select_repository(r))

        with container:
            # Repository name과 status badge
            with ui.row().style('display: flex; align-items: center; gap: 8px; margin-bottom: 4px;'):
                ui.html(f'<span style="color: #2563eb; font-size: 18px;">📁</span>')
                ui.html(f'<span style="font-weight: 600;">{repo["name"]}</span>')
                # Status badge
                status = repo.get("status", "active")
                status_colors = {
                    'pending': 'background-color: #fef3c7; color: #92400e;',
                    'syncing': 'background-color: #fef3c7; color: #92400e;',
                    'active': 'background-color: #d1fae5; color: #065f46;',
                    'error': 'background-color: #fee2e2; color: #991b1b;'
                }
                status_style = status_colors.get(status, 'background-color: #e5e7eb; color: #374151;')
                ui.html(f'<span style="{status_style} padding: 2px 8px; border-radius: 9999px; font-size: 10px; font-weight: 600;">{status.upper()}</span>')

            # 에러 메시지 표시 (에러 상태일 때만) - description 위에 표시
            error_message = repo.get("error_message")
            if status == 'error':
                if error_message and error_message.strip():
                    # 에러 메시지를 더 명확하게 표시 (더 크고 눈에 띄게)
                    ui.html(f'<div style="font-size: 12px; color: #991b1b; background-color: #fee2e2; padding: 8px; border-radius: 6px; margin-bottom: 6px; border-left: 3px solid #dc2626; font-weight: 500;">⚠️ {error_message}</div>')
                else:
                    # 디버깅: error_message 값 확인
                    ui.html(f'<div style="font-size: 12px; color: #991b1b; background-color: #fee2e2; padding: 8px; border-radius: 6px; margin-bottom: 6px; border-left: 3px solid #dc2626; font-weight: 500;">⚠️ Error (no message): {repr(error_message)}</div>')

            ui.html(f'<div style="font-size: 14px; color: #6b7280; margin-bottom: 4px;">{repo.get("description", "")}</div>')

            # File count와 collections count 표시
            file_count = repo.get("file_count", 0)
            collections_count = repo.get("collections_count", 0)
            ui.html(f'<div style="font-size: 12px; color: #9ca3af;">📄 {file_count} files • 🗄️ {collections_count} collections</div>')

        # Store reference for later updates
        self.repo_containers[repo["id"]] = container

    def render_main_content(self):
        self.main_content_container = ui.column().style('flex: 1; height: 100%; padding: 24px; overflow-y: auto; background-color: white;')
        with self.main_content_container:
            if not self.selected_repo:
                self.render_empty_state()
            else:
                self.render_repository_details()

    def render_empty_state(self):
        with ui.column().style('width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; text-align: center;'):
            ui.html('<span style="font-size: 72px; color: #9ca3af;">📂</span>')
            ui.html('<h3 style="font-size: 20px; font-weight: 600; color: #4b5563; margin: 16px 0 8px 0;">Select a Repository</h3>')
            ui.html('<p style="color: #6b7280;">Choose a repository from the sidebar to view its details and settings</p>')

    def render_repository_details(self):
        repo = self.selected_repo

        with ui.column().style('width: 100%; gap: 24px;'):
            # Header section
            with ui.row().style('width: 100%; display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px;'):
                with ui.row().style('display: flex; align-items: center; gap: 12px;'):
                    ui.html('<span style="color: #2563eb; font-size: 32px;">📁</span>')
                    ui.html(f'<h2 style="font-size: 24px; font-weight: 700; margin: 0;">{repo["name"]}</h2>')
                    self.render_status_badge(repo["status"])


            # Content section
            with ui.column().style('width: 100%; gap: 24px;'):
                self.render_repository_info()
                self.render_sync_status()
                self.render_quick_actions()

    def render_repository_info(self):
        repo = self.selected_repo
        with ui.column().style('background-color: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 20px;'):
            ui.html('<h3 style="font-size: 18px; font-weight: 600; margin-bottom: 16px;">Repository Information</h3>')

            # owner 정보는 User 객체에서 가져와야 하므로 임시로 owner_id 표시
            owner_display = repo.get("owner", "Unknown")

            # created_at과 last_sync는 datetime 객체일 수도 있고 None일 수도 있음
            created_at = repo.get("created_at")
            last_sync = repo.get("last_sync")

            created_display = created_at.strftime("%b %d, %Y") if created_at else "N/A"
            last_sync_display = last_sync.strftime("%b %d, %Y at %H:%M") if last_sync else "Not synced yet"

            info_items = [
                ("Owner", owner_display),
                ("URL", repo.get("url", "")),
                ("File Count", f'{repo.get("file_count", 0):,}'),
                ("Collections", f'{repo.get("collections_count", 0):,}'),
                ("Created", created_display),
                ("Last Sync", last_sync_display)
            ]

            for label, value in info_items:
                with ui.row().style('display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid #f3f4f6;'):
                    ui.html(f'<span style="font-weight: 500; color: #374151;">{label}</span>')
                    if label == "URL":
                        ui.html(f'<a href="{value}" target="_blank" style="color: #2563eb; text-decoration: none;">{value}</a>')
                    else:
                        ui.html(f'<span style="color: #6b7280;">{value}</span>')

    def render_sync_status(self):
        repo = self.selected_repo
        with ui.column().style('background-color: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 20px;'):
            ui.html('<h3 style="font-size: 18px; font-weight: 600; margin-bottom: 16px;">Synchronization Status</h3>')

            with ui.row().style('display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid #f3f4f6;'):
                ui.html('<span style="font-weight: 500; color: #374151;">Vector Database</span>')
                self.render_vectordb_status(repo["vectordb_status"])

            with ui.row().style('display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid #f3f4f6;'):
                ui.html('<span style="font-weight: 500; color: #374151;">Collections</span>')
                ui.html(f'<span style="color: #6b7280;">{repo["collections_count"]} active</span>')

    def render_quick_actions(self):
        with ui.column().style('background-color: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 20px;'):
            ui.html('<h3 style="font-size: 18px; font-weight: 600; margin-bottom: 16px;">Actions</h3>')

            # Admin actions
            actions = []

            if self.auth_service.is_admin():
                actions.extend([
                    ("🔄 Sync Repository", lambda: self.sync_repository()),
                    ("👥 Manage Members", lambda: self.show_members_dialog()),
                    ("🗑️ Delete Repository", lambda: self.show_delete_repository_dialog())
                ])

            for label, action in actions:
                ui.button(label, on_click=action).style('width: 100%; text-align: left; background-color: #f9fafb; border: 1px solid #e5e7eb; padding: 8px 12px; border-radius: 6px; margin-bottom: 4px;')

    def render_members_preview(self):
        with ui.column().style('background-color: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 20px;'):
            ui.html('<h3 style="font-size: 18px; font-weight: 600; margin-bottom: 16px;">Members</h3>')

            try:
                members = self.api_service.get_repository_members(self.selected_repo["id"])[:3]
            except Exception as e:
                ui.notify(f"Failed to load members: {str(e)}", type='negative')
                members = []

            for member in members:
                with ui.row().style('display: flex; align-items: center; gap: 12px; margin-bottom: 12px;'):
                    ui.html('<div style="width: 32px; height: 32px; background-color: #dbeafe; color: #2563eb; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 14px;">👤</div>')
                    ui.html(f'<div><div style="font-weight: 500;">{member["username"]}</div><div style="font-size: 12px; color: #6b7280;">{member["role"]}</div></div>')

            try:
                total_members = len(self.api_service.get_repository_members(self.selected_repo["id"]))
                if total_members > 3:
                    ui.html(f'<div style="text-align: center; font-size: 12px; color: #6b7280;">... and {total_members - 3} more</div>')
            except Exception as e:
                pass

    def render_status_badge(self, status):
        colors = {
            'active': 'bg-green-100 text-green-800',
            'syncing': 'bg-yellow-100 text-yellow-800',
            'error': 'bg-red-100 text-red-800'
        }
        ui.html(f'<span class="px-3 py-1 rounded-full text-sm {colors.get(status, "bg-gray-100 text-gray-800")}">{status}</span>')

    def render_vectordb_status(self, status):
        colors = {
            'healthy': 'bg-green-100 text-green-800',
            'syncing': 'bg-yellow-100 text-yellow-800',
            'error': 'bg-red-100 text-red-800'
        }
        ui.html(f'<span class="px-2 py-1 rounded-full text-xs {colors.get(status, "bg-gray-100 text-gray-800")}">{status}</span>')

    def select_repository(self, repo):
        self.selected_repo = repo

        # Update sidebar selection appearance
        for repo_id, container in self.repo_containers.items():
            if repo_id == repo["id"]:
                # Selected style
                container.style('width: 100%; padding: 12px; margin-bottom: 8px; border-radius: 8px; cursor: pointer; border: 2px solid #3b82f6; background-color: #dbeafe;')
            else:
                # Unselected style
                container.style('width: 100%; padding: 12px; margin-bottom: 8px; border-radius: 8px; cursor: pointer; border: 1px solid #e5e7eb; background-color: white;')

        # Update the main content area
        self.main_content_container.clear()
        with self.main_content_container:
            if not self.selected_repo:
                self.render_empty_state()
            else:
                self.render_repository_details()

    def show_add_repository_dialog(self):
        with ui.dialog() as dialog, ui.card().classes('w-96'):
            ui.html('<h3 class="text-lg font-semibold mb-4">Add New Repository</h3>')

            with ui.column().classes('gap-4'):
                repo_url = ui.input('Repository URL', placeholder='https://github.com/owner/repo').classes('rag-input w-full')
                description = ui.textarea('Description', placeholder='Optional description').classes('rag-input w-full')

                with ui.row().classes('gap-2 mt-4'):
                    ui.button('Cancel', on_click=dialog.close).classes('rag-button-secondary')
                    ui.button('Add Repository', on_click=lambda: self.add_repository(repo_url.value, description.value, dialog)).classes('rag-button-primary')

        dialog.open()

    def add_repository(self, url, description, dialog):
        if not url:
            ui.notify('Please enter a repository URL', color='red')
            return

        try:
            # GitHub URL에서 repository name 추출
            # 예: https://github.com/owner/repo -> repo
            repo_name = url.rstrip('/').split('/')[-1]

            # API 호출하여 repository 생성
            created_repo = self.api_service.create_repository(
                name=repo_name,
                url=url,
                description=description or f"Repository: {repo_name}",
                is_public=False
            )

            ui.notify(f'Repository "{repo_name}" added successfully! Processing...', color='green')
            dialog.close()

            # 상태 체크를 위한 타이머 시작 (reload 전에)
            self.start_repository_status_check(created_repo['id'], repo_name)

        except Exception as e:
            error_detail = str(e)
            # 에러 메시지에서 실제 DB 에러나 상세 내용 추출
            if 'detail' in error_detail:
                try:
                    import json
                    error_data = json.loads(error_detail.split("'detail': ")[1].split("}")[0] + "}")
                    error_detail = error_data
                except:
                    pass
            ui.notify(f'Failed to add repository: {error_detail}', color='red', timeout=10000)

    def start_repository_status_check(self, repo_id: str, repo_name: str):
        """Repository 처리 상태를 주기적으로 확인"""
        check_count = 0
        max_checks = 60  # 최대 60번 확인 (약 1분)

        def check_status():
            nonlocal check_count
            check_count += 1

            try:
                status_data = self.api_service.get_repository_status(repo_id)
                current_status = status_data.get('status')
                error_message = status_data.get('error_message')

                # 에러 상태 확인
                if current_status == 'error':
                    # 타이머 중지
                    if hasattr(self, 'status_timer'):
                        self.status_timer.active = False
                    # 에러 메시지가 있으면 함께 표시
                    if error_message:
                        ui.notify(f'❌ Failed to process repository "{repo_name}": {error_message}', color='negative', timeout=15000)
                    else:
                        ui.notify(f'❌ Failed to process repository "{repo_name}". Please check the repository URL and try again.', color='negative', timeout=10000)
                    # 페이지 새로고침하여 에러 메시지를 사이드바에 표시
                    ui.navigate.reload()
                    return

                # 완료 상태 확인
                if current_status == 'active':
                    # 타이머 중지
                    if hasattr(self, 'status_timer'):
                        self.status_timer.active = False
                    ui.notify(f'✅ Repository "{repo_name}" processed successfully!', color='positive', timeout=5000)
                    # 페이지 새로고침하여 업데이트된 상태 표시
                    ui.navigate.reload()
                    return

                # 최대 확인 횟수 초과
                if check_count >= max_checks:
                    if hasattr(self, 'status_timer'):
                        self.status_timer.active = False
                    ui.notify(f'⏱️ Repository "{repo_name}" is still processing. Please check back later.', color='info', timeout=5000)
                    return

            except Exception as e:
                print(f"Status check error: {e}")
                # 에러 발생 시 타이머 중지
                if check_count >= 5:  # 5번 실패하면 중지
                    if hasattr(self, 'status_timer'):
                        self.status_timer.active = False

        # 1초마다 상태 확인 (더 빠른 응답)
        self.status_timer = ui.timer(1.0, check_status)

    def show_members_dialog(self):
        with ui.dialog() as dialog, ui.card().style('width: 600px;'):
            with ui.row().style('display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;'):
                ui.html('<h3 style="font-size: 18px; font-weight: 600;">Repository Members</h3>')
                ui.button('➕ Invite Member', on_click=lambda: self.show_invite_member_dialog(dialog)).style('background-color: #3b82f6; color: white; padding: 6px 12px; border-radius: 4px; border: none; font-size: 12px;')

            try:
                members = self.api_service.get_repository_members(self.selected_repo["id"])
            except Exception as e:
                ui.notify(f"Failed to load members: {str(e)}", type='negative')
                members = []

            with ui.column().style('gap: 8px; max-height: 400px; overflow-y: auto;'):
                for member in members:
                    with ui.row().style('display: flex; align-items: center; justify-content: space-between; padding: 12px; border: 1px solid #e5e7eb; border-radius: 8px;'):
                        with ui.row().style('display: flex; align-items: center; gap: 12px;'):
                            ui.html('<div style="width: 40px; height: 40px; background-color: #dbeafe; color: #2563eb; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 16px;">👤</div>')
                            with ui.column().style('gap: 2px;'):
                                ui.html(f'<div style="font-weight: 500; font-size: 14px;">{member["username"]}</div>')
                                ui.html(f'<div style="font-size: 12px; color: #6b7280;">{member["email"]}</div>')
                                ui.html(f'<div style="font-size: 11px; color: #9ca3af;">Joined {member["joined_at"].strftime("%b %d, %Y")}</div>')

                        with ui.row().style('display: flex; align-items: center; gap: 8px;'):
                            # Role dropdown
                            role_select = ui.select(['admin', 'member'], value=member["role"], on_change=lambda e, m=member: self.change_member_role(m, e.value)).style('min-width: 80px; font-size: 12px;')

                            # Action buttons (only show if not current user or if admin)
                            current_user = self.auth_service.get_current_user()
                            if current_user["email"] != member["email"]:
                                ui.button('🚪', on_click=lambda m=member: self.kick_member(m, dialog)).style('background-color: #fef2f2; color: #dc2626; padding: 4px; border-radius: 4px; border: none; font-size: 12px; cursor: pointer;').tooltip('Remove member')

            ui.button('Close', on_click=dialog.close).style('width: 100%; margin-top: 16px; background-color: #6b7280; color: white; padding: 8px; border-radius: 4px; border: none;')

        dialog.open()

    def sync_repository(self):
        """레포지토리 동기화 시작"""
        if not self.selected_repo:
            ui.notify('Please select a repository first', color='red')
            return

        repo_id = self.selected_repo["id"]
        repo_name = self.selected_repo["name"]

        try:
            ui.notify(f'🔄 Starting synchronization for "{repo_name}"...', color='blue')

            # API 호출하여 동기화 시작
            result = self.api_service.sync_repository(repo_id)

            if result.get("success"):
                ui.notify(f'✅ Synchronization task started for "{repo_name}"', color='positive')
                # 상태 체크 시작
                self.start_sync_status_check(repo_id, repo_name)
            else:
                error_msg = result.get("error", "Unknown error")
                ui.notify(f'❌ Failed to start synchronization: {error_msg}', color='negative')

        except Exception as e:
            ui.notify(f'❌ Failed to sync repository: {str(e)}', color='negative')

    def start_sync_status_check(self, repo_id: str, repo_name: str):
        """동기화 상태를 주기적으로 확인"""
        check_count = 0
        max_checks = 120  # 최대 120번 확인 (약 2분)

        def check_status():
            nonlocal check_count
            check_count += 1

            try:
                status_data = self.api_service.get_repository_status(repo_id)
                current_status = status_data.get('status')
                vectordb_status = status_data.get('vectordb_status')
                error_message = status_data.get('error_message')

                # 에러 상태 확인
                if current_status == 'error' or vectordb_status == 'error':
                    if hasattr(self, 'sync_timer'):
                        self.sync_timer.active = False
                    if error_message:
                        ui.notify(f'❌ Sync failed for "{repo_name}": {error_message}', color='negative', timeout=15000)
                    else:
                        ui.notify(f'❌ Sync failed for "{repo_name}". Please try again.', color='negative', timeout=10000)
                    ui.navigate.reload()
                    return

                # 완료 상태 확인
                if current_status == 'active' and vectordb_status == 'active':
                    if hasattr(self, 'sync_timer'):
                        self.sync_timer.active = False
                    ui.notify(f'✅ Repository "{repo_name}" synchronized successfully!', color='positive', timeout=5000)
                    ui.navigate.reload()
                    return

                # 최대 확인 횟수 초과
                if check_count >= max_checks:
                    if hasattr(self, 'sync_timer'):
                        self.sync_timer.active = False
                    ui.notify(f'⏱️ Sync is still in progress for "{repo_name}". Please check back later.', color='info', timeout=5000)
                    return

            except Exception as e:
                print(f"Sync status check error: {e}")
                if check_count >= 5:
                    if hasattr(self, 'sync_timer'):
                        self.sync_timer.active = False

        # 1초마다 상태 확인
        self.sync_timer = ui.timer(1.0, check_status)

    def show_sync_logs(self):
        ui.notify('Sync logs feature coming soon', color='blue')

    def show_repository_settings(self):
        with ui.dialog() as dialog, ui.card().classes('w-96'):
            ui.html('<h3 class="text-lg font-semibold mb-4">Repository Settings</h3>')

            with ui.column().classes('gap-4'):
                ui.input('Repository Name', value=self.selected_repo["name"]).classes('w-full')
                ui.textarea('Description', value=self.selected_repo["description"]).classes('w-full')

                with ui.row().classes('items-center gap-2'):
                    ui.label('Auto Sync')
                    ui.switch(value=True)

                with ui.row().classes('items-center gap-2'):
                    ui.label('Public Access')
                    ui.switch(value=False)

                with ui.row().classes('gap-2 mt-4'):
                    ui.button('Cancel', on_click=dialog.close).classes('rag-button-secondary')
                    ui.button('Save Settings', on_click=lambda: self.save_repository_settings(dialog)).classes('rag-button-primary')

        dialog.open()

    def save_repository_settings(self, dialog):
        ui.notify('Repository settings saved!', color='green')
        dialog.close()

    def show_delete_repository_dialog(self):
        with ui.dialog() as dialog, ui.card().classes('w-96'):
            ui.html('<h3 class="text-lg font-semibold text-red-600 mb-4">Delete Repository</h3>')
            ui.html('<p class="text-gray-600 mb-4">This action cannot be undone. The repository will be permanently removed from the system.</p>')

            confirm_input = ui.input('Type "DELETE" to confirm', placeholder='DELETE').classes('w-full')

            with ui.row().classes('gap-2 mt-6 w-full'):
                ui.button('Cancel', on_click=dialog.close).classes('rag-button-secondary flex-1')
                ui.button('Delete Repository', on_click=lambda: self.delete_repository(confirm_input.value, dialog)).classes('bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 flex-1')

        dialog.open()

    def delete_repository(self, confirmation, dialog):
        if confirmation != "DELETE":
            ui.notify('Please type "DELETE" to confirm', color='red')
            return

        ui.notify('Repository deletion is not available in demo mode', color='blue')
        dialog.close()

    def change_member_role(self, member, new_role):
        """Change a member's role"""
        old_role = member["role"]
        if old_role != new_role:
            member["role"] = new_role
            ui.notify(f'{member["username"]} role changed from {old_role} to {new_role}', color='green')
        else:
            ui.notify('Role unchanged', color='blue')

    def kick_member(self, member, dialog):
        """Remove a member from the repository"""
        current_user = self.auth_service.get_current_user()
        if current_user["email"] == member["email"]:
            ui.notify('You cannot remove yourself', color='red')
            return

        # Show confirmation dialog
        with ui.dialog() as confirm_dialog, ui.card().style('width: 400px;'):
            ui.html(f'<h3 style="font-size: 16px; font-weight: 600; margin-bottom: 12px;">Remove Member</h3>')
            ui.html(f'<p style="margin-bottom: 16px;">Are you sure you want to remove <strong>{member["username"]}</strong> from this repository?</p>')

            with ui.row().style('display: flex; gap: 8px; justify-content: flex-end;'):
                ui.button('Cancel', on_click=confirm_dialog.close).style('background-color: #6b7280; color: white; padding: 6px 12px; border-radius: 4px; border: none;')
                ui.button('Remove', on_click=lambda: self.confirm_kick_member(member, confirm_dialog, dialog)).style('background-color: #dc2626; color: white; padding: 6px 12px; border-radius: 4px; border: none;')

        confirm_dialog.open()

    def confirm_kick_member(self, member, confirm_dialog, members_dialog):
        """Confirm member removal"""
        # In a real app, this would remove from database
        ui.notify(f'{member["username"]} has been removed from the repository', color='green')
        confirm_dialog.close()
        members_dialog.close()
        # Refresh the members dialog
        self.show_members_dialog()

    def show_invite_member_dialog(self, parent_dialog):
        """Show dialog to invite new member"""
        with ui.dialog() as invite_dialog, ui.card().style('width: 400px;'):
            ui.html('<h3 style="font-size: 16px; font-weight: 600; margin-bottom: 12px;">Invite Member</h3>')

            with ui.column().style('gap: 12px;'):
                email_input = ui.input('Email Address', placeholder='user@example.com').style('width: 100%;')
                role_select = ui.select(['member', 'admin'], value='member', label='Role').style('width: 100%;')

                with ui.row().style('display: flex; gap: 8px; justify-content: flex-end; margin-top: 16px;'):
                    ui.button('Cancel', on_click=invite_dialog.close).style('background-color: #6b7280; color: white; padding: 6px 12px; border-radius: 4px; border: none;')
                    ui.button('Send Invite', on_click=lambda: self.send_invite(email_input.value, role_select.value, invite_dialog)).style('background-color: #3b82f6; color: white; padding: 6px 12px; border-radius: 4px; border: none;')

        invite_dialog.open()

    def send_invite(self, email, role, dialog):
        """Send invitation to new member"""
        if not email or '@' not in email:
            ui.notify('Please enter a valid email address', color='red')
            return

        # In a real app, this would send an actual invitation
        ui.notify(f'Invitation sent to {email} as {role}', color='green')
        dialog.close()