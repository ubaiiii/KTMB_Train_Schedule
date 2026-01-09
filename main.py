import flet as ft
import pandas as pd
import requests
import io
from datetime import datetime

# Configuration
GITHUB_BASE_URL = "https://raw.githubusercontent.com/ubaiiii/KTMB_Train_Schedule/main/timetables/"
ROUTES = [
    "batu_caves-pulau_sebang", "pulau_sebang-batu_caves",
    "tg_malim-pel_klang", "pel_klang-tg_malim",
    "padang_besar-ipoh", "ipoh-padang_besar",
    "butterworth-padang_besar", "padang_besar-butterworth"
    # Add all 12 routes from your repo here
]

class KomuterApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "KTMB Komuter Tracker"
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.padding = 20
        self.df = None
        
        # UI Elements
        self.route_dd = ft.Dropdown(
            label="Select Route",
            options=[ft.dropdown.Option(r.replace("_", " ").title()) for r in ROUTES],
            on_change=self.load_route_data,
            border_radius=10
        )
        self.origin_dd = ft.Dropdown(label="Origin", visible=False, border_radius=10)
        self.dest_dd = ft.Dropdown(label="Destination", visible=False, border_radius=10)
        self.search_btn = ft.ElevatedButton(
            "Find Trains", 
            on_click=self.search_trains, 
            visible=False,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))
        )
        self.results_list = ft.ListView(expand=True, spacing=10, padding=10)
        self.loader = ft.ProgressBar(visible=False, color="blue")

        # Layout
        self.page.add(
            ft.Text("KTMB Mobile Schedule", size=28, weight="bold", color="blue700"),
            ft.Text("Real-time timetable tracker", size=14, color="grey700"),
            ft.Divider(height=20, color="transparent"),
            self.route_dd,
            self.origin_dd,
            self.dest_dd,
            self.loader,
            ft.Row([self.search_btn], alignment=ft.MainAxisAlignment.CENTER),
            ft.Divider(),
            self.results_list
        )

    def load_route_data(self, e):
        self.loader.visible = True
        self.page.update()
        
        # Construct filename from selection
        route_file = self.route_dd.value.lower().replace(" ", "_") + ".parquet"
        url = f"{GITHUB_BASE_URL}{route_file}"
        
        try:
            response = requests.get(url)
            self.df = pd.read_parquet(io.BytesIO(response.content))
            
            # Update Station Dropdowns
            stations = self.df.columns[1:].tolist() # Assuming first col is Train ID/Time
            self.origin_dd.options = [ft.dropdown.Option(s) for s in stations]
            self.dest_dd.options = [ft.dropdown.Option(s) for s in stations]
            
            self.origin_dd.visible = True
            self.dest_dd.visible = True
            self.search_btn.visible = True
        except Exception as ex:
            self.page.snack_bar = ft.SnackBar(ft.Text(f"Error loading data: {ex}"))
            self.page.snack_bar.open = True
        
        self.loader.visible = False
        self.page.update()

    def search_trains(self, e):
        if not self.origin_dd.value or not self.dest_dd.value:
            return

        self.results_list.controls.clear()
        now = datetime.now().strftime("%H:%M")
        
        # Filter Logic (Based on your Streamlit logic)
        # 1. Get schedule for Origin and Destination
        relevant_data = self.df[['No. Tren', self.origin_dd.value, self.dest_dd.value]]
        
        # 2. Filter for future trains
        future_trains = relevant_data[relevant_data[self.origin_dd.value] > now].sort_values(by=self.origin_dd.value)

        if future_trains.empty:
            self.results_list.controls.append(ft.Text("No more trains today 😴", text_align="center"))
        else:
            for _, row in future_trains.head(10).iterrows():
                self.results_list.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Text(f"Train {row['No. Tren']}", weight="bold", size=16),
                                ft.Container(
                                    content=ft.Text("On Time", size=12, color="white"),
                                    bgcolor="green500",
                                    padding=5,
                                    border_radius=5
                                )
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ft.Divider(),
                            ft.Row([
                                ft.Column([ft.Text("Origin"), ft.Text(row[self.origin_dd.value], size=20, weight="bold")]),
                                ft.Icon(ft.icons.ARROW_FORWARD_ROUNDED),
                                ft.Column([ft.Text("Arrival"), ft.Text(row[self.dest_dd.value], size=20, weight="bold")], horizontal_alignment="end"),
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                        ]),
                        padding=15,
                        border_radius=15,
                        bgcolor="blueGrey50",
                        border=ft.border.all(1, "blueGrey100")
                    )
                )
        
        self.page.update()

# ft.app(target=KomuterApp)
ft.run(KomuterApp)