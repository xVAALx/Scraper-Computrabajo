import re
import pandas as pd
from playwright.sync_api import sync_playwright
from datetime import datetime

ciudad_pattern = re.compile(
    r"\b([A-ZÁÉÍÓÚÑÜ][a-záéíóúñü]+(?:\s+(?:de|del|la|las|los|el)\s+)?"
    r"(?:[A-ZÁÉÍÓÚÑÜ][a-záéíóúñü]+)*)\b"
)

ubicacion_pattern = re.compile(
    r"^(?:[A-ZÁÉÍÓÚÑÜ][a-záéíóúñü]+(?:\s+(?:de|del|la|las|los|el)\s+)?"
    r"(?:[A-ZÁÉÍÓÚÑÜ][a-záéíóúñü]+)*)(?:,\s*.*)?$"
)

DEFAULT_OFFER = {
    "Titulo": "Titulo no encontrado",
    "Empresa": "Empresa no encontrada",
    "Ubicacion": "No especificada",
    "Salario": "No especificado",
    "Modalidad": "No especificada",
    "Link": "No disponible",
}

def clean_text(value):
    if not value:
        return None
    return " ".join(value.split())

def defaults():
    return DEFAULT_OFFER.copy()


def extract_offer_data(oferta):
    """Extrae todos los datos parseando el HTML con Python."""
    try:
        html = oferta.inner_html()  # 1 sola llamada al navegador
    except Exception:
        return defaults()

    m = re.search(r'<a class="js-o-link[^"]*"[^>]*>([^<]+)</a>', html)
    titulo = m.group(1).strip() if m else "Titulo no encontrado"

    m = re.search(r'<a class="js-o-link[^"]*"[^>]*href="([^"]+)"', html)
    href = m.group(1) if m else None
    full_link = f"https://ar.computrabajo.com{href}" if href else "No disponible"

    m = re.search(r'a[^>]*offer-grid-article-company-url[^>]*>([^<]+)</a>', html)
    empresa = m.group(1).strip() if m else "Empresa no encontrada"
    if empresa == "Empresa no encontrada":
        if 'importante empresa' in html.lower():
            empresa = "Importante empresa del sector"

    m = re.search(r'<p class="fs16 fc_base mt5"[^>]*>\s*<span[^>]*>([^<]+)</span>', html)
    ubicacion = m.group(1).strip() if m else "No especificada"

    m = re.search(r'<span class="icon i_salary"[^>]*></span>([^<]+)', html)
    salario = m.group(1).strip() if m else "No especificado"

    if '.icon.i_home_office' in html or 'Remoto' in html or 'Híbrido' in html:
        modalidad = "Remoto/Híbrido"
    elif '.icon.i_home' in html:
        modalidad = "Remoto"
    else:
        modalidad = "No especificada"
    return {
        "Titulo": titulo,
        "Empresa": empresa,
        "Ubicacion": ubicacion,
        "Salario": salario,
        "Modalidad": modalidad,
        "Link": full_link,
    }

def scrape_ofertas():
    with sync_playwright() as p:

        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        page.goto("https://ar.computrabajo.com/empleos-de-data")
        page.wait_for_load_state("networkidle", timeout=30000)
        page.wait_for_selector(".box_offer")


        #contamos la cantidad de paginas
        try:
            total_texto = page.locator(".title_page .fwB").text_content()
            total_ofertas = int(total_texto.strip())
        except Exception:
            total_ofertas = 0

        if total_ofertas > 0:
            ofertas_por_pagina = 20
            total_paginas = (total_ofertas + ofertas_por_pagina - 1) // ofertas_por_pagina
        else:
            total_paginas = 0

#Creacion de los data frames.
        datos = []
        for pagina in range(1, total_paginas + 1):
            url = f"https://ar.computrabajo.com/empleos-de-data?p={pagina}"
            print(f"Pagina {pagina}...")

            page.goto(url)
            page.wait_for_load_state("networkidle", timeout=30000)
            page.wait_for_selector(".box_offer", timeout=10000)

            ofertas = page.locator(".box_offer").all()
            print(f"Encontré {len(ofertas)} ofertas\n")

            for oferta in ofertas[:20]:
                data = extract_offer_data(oferta)
                datos.append(data)

        if datos:
            df = pd.DataFrame(datos)
            nombre = f"ofertas_data_{datetime.now():%Y-%m-%d}.csv"
            df.to_csv(f"data/raw/{nombre}", index=False)
            print(f"Guardado en data/raw/{nombre} ({len(df)} ofertas)")
        else:
            print("No se encontraron ofertas para exportar.")

        browser.close()


if __name__ == "__main__":
    scrape_ofertas()
