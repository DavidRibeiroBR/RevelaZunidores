// RevelaZunidores - add-on do ReShade para Atomic Heart
//
// Desenha DENTRO da imagem do jogo (funciona ate em tela cheia exclusiva):
//   - marcadores nos colecionaveis, visiveis atraves das paredes
//   - seta na borda da tela apontando o item mais proximo
//   - bussola no topo
// Os dados vem do mod Lua RevelaZunidores (UE4SS), que grava:
//   <pasta do jogo>\ue4ss\Mods\RevelaZunidores\camera.json  (a cada 50 ms)
//   <pasta do jogo>\ue4ss\Mods\RevelaZunidores\estado.json  (a cada 500 ms)
// Configuracoes: menu do ReShade (tecla Home) > aba Add-ons > RevelaZunidores.
// Atalho no jogo: Ctrl+Shift+I liga/desliga os indicadores.

#define ImTextureID ImU64
#define NOMINMAX
#include <windows.h>
#include <imgui.h>
#include <reshade.hpp>

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <map>
#include <string>
#include <utility>
#include <vector>

extern "C" __declspec(dllexport) const char *NAME = "RevelaZunidores";
extern "C" __declspec(dllexport) const char *DESCRIPTION =
    "Markers, arrow and compass for Atomic Heart collectibles (data from the RevelaZunidores UE4SS mod).";

namespace
{
// ---------------------------------------------------------------------------
// JSON minimo (so o necessario para estado.json/camera.json)
// ---------------------------------------------------------------------------
struct Valor
{
    enum Tipo { Nulo, Bool, Num, Txt, Lista, Obj } t = Nulo;
    bool b = false;
    double n = 0;
    std::string s;
    std::vector<Valor> a;
    std::vector<std::pair<std::string, Valor>> o;

    const Valor *campo(const char *k) const
    {
        if (t != Obj) return nullptr;
        for (const auto &p : o)
            if (p.first == k) return &p.second;
        return nullptr;
    }
    double num(const char *k, double d = 0) const { const Valor *v = campo(k); return v && v->t == Num ? v->n : d; }
    bool boo(const char *k, bool d = false) const { const Valor *v = campo(k); return v && v->t == Bool ? v->b : d; }
    std::string txt(const char *k) const { const Valor *v = campo(k); return v && v->t == Txt ? v->s : std::string(); }
};

struct Leitor
{
    const char *p, *e;
    bool ok = true;

    void ws() { while (p < e && (*p == ' ' || *p == '\n' || *p == '\r' || *p == '\t')) ++p; }
    bool pega(char c) { ws(); if (p < e && *p == c) { ++p; return true; } return false; }

    static void utf8(std::string &out, unsigned cp)
    {
        if (cp < 0x80) out += char(cp);
        else if (cp < 0x800) { out += char(0xC0 | (cp >> 6)); out += char(0x80 | (cp & 0x3F)); }
        else { out += char(0xE0 | (cp >> 12)); out += char(0x80 | ((cp >> 6) & 0x3F)); out += char(0x80 | (cp & 0x3F)); }
    }

    std::string texto()
    {
        std::string r;
        if (!pega('"')) { ok = false; return r; }
        while (p < e && *p != '"')
        {
            if (*p == '\\' && p + 1 < e)
            {
                ++p;
                switch (*p)
                {
                case 'n': r += '\n'; break;
                case 't': r += '\t'; break;
                case 'r': r += '\r'; break;
                case 'b': r += '\b'; break;
                case 'f': r += '\f'; break;
                case 'u':
                    if (p + 4 < e) { utf8(r, unsigned(strtoul(std::string(p + 1, p + 5).c_str(), nullptr, 16))); p += 4; }
                    break;
                default: r += *p; break;
                }
                ++p;
            }
            else r += *p++;
        }
        if (p < e) ++p; else ok = false;
        return r;
    }

    Valor valor(int prof = 0)
    {
        Valor v;
        ws();
        if (p >= e || prof > 32) { ok = false; return v; }
        if (*p == '{')
        {
            ++p; v.t = Valor::Obj;
            if (pega('}')) return v;
            do { std::string k = texto(); if (!pega(':')) { ok = false; return v; } v.o.emplace_back(std::move(k), valor(prof + 1)); } while (ok && pega(','));
            if (!pega('}')) ok = false;
        }
        else if (*p == '[')
        {
            ++p; v.t = Valor::Lista;
            if (pega(']')) return v;
            do v.a.push_back(valor(prof + 1)); while (ok && pega(','));
            if (!pega(']')) ok = false;
        }
        else if (*p == '"') { v.t = Valor::Txt; v.s = texto(); }
        else if (e - p >= 4 && !strncmp(p, "true", 4)) { v.t = Valor::Bool; v.b = true; p += 4; }
        else if (e - p >= 5 && !strncmp(p, "false", 5)) { v.t = Valor::Bool; p += 5; }
        else if (e - p >= 4 && !strncmp(p, "null", 4)) { p += 4; }
        else
        {
            char *fim = nullptr;
            v.t = Valor::Num; v.n = strtod(p, &fim);
            if (fim == p) ok = false; else p = fim;
        }
        return v;
    }
};

bool ler_json(const std::wstring &caminho, Valor &saida, FILETIME &mtime_visto)
{
    WIN32_FILE_ATTRIBUTE_DATA at;
    if (!GetFileAttributesExW(caminho.c_str(), GetFileExInfoStandard, &at)) return false;
    if (CompareFileTime(&at.ftLastWriteTime, &mtime_visto) == 0) return false; // sem mudanca
    // compartilha leitura/escrita/exclusao para nao travar o os.remove/os.rename do Lua
    HANDLE h = CreateFileW(caminho.c_str(), GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
                           nullptr, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (h == INVALID_HANDLE_VALUE) return false;
    std::string dados;
    char buf[65536];
    DWORD lidos = 0;
    while (ReadFile(h, buf, sizeof(buf), &lidos, nullptr) && lidos > 0) dados.append(buf, lidos);
    CloseHandle(h);
    Leitor l{ dados.data(), dados.data() + dados.size() };
    Valor v = l.valor();
    if (!l.ok || v.t != Valor::Obj) return false;
    saida = std::move(v);
    mtime_visto = at.ftLastWriteTime;
    return true;
}

double idade_arquivo(const std::wstring &caminho)
{
    WIN32_FILE_ATTRIBUTE_DATA at;
    if (!GetFileAttributesExW(caminho.c_str(), GetFileExInfoStandard, &at)) return 1e9;
    FILETIME agora; GetSystemTimeAsFileTime(&agora);
    ULARGE_INTEGER a, b;
    a.LowPart = agora.dwLowDateTime; a.HighPart = agora.dwHighDateTime;
    b.LowPart = at.ftLastWriteTime.dwLowDateTime; b.HighPart = at.ftLastWriteTime.dwHighDateTime;
    return a.QuadPart > b.QuadPart ? double(a.QuadPart - b.QuadPart) / 1e7 : 0.0;
}

// ---------------------------------------------------------------------------
// estado
// ---------------------------------------------------------------------------
struct Item { std::string nome; double x, y, z; bool oculto; };
struct Categoria { int i; std::string nome; std::string conteudo; int total; double dist; std::vector<Item> itens; std::string nome_en, nome_pt; };

struct Config
{
    bool ativo = true, marcadores = true, nomes = false, seta = true, bussola = true, esconder_ocultos = false;
    int max_marcadores = 40;
    // categorias NAO reveladas, no formato ",3,7," (categorias novas ficam reveladas por padrao).
    // Independente da categoria do medidor/F5 do mod.
    std::string ocultas = ",";
    // ajustes de distancia de exibicao feitos no ReShade, por categoria: "3=40;7=0;"
    // (0 = sem limite). Categoria sem ajuste usa a distancia informada pelo mod
    // (config.lua: DISTANCIA_PADRAO_M / "distancia" da categoria, ou o que a janela definiu).
    std::string distancias;
    int idioma = 0; // 0 = segue o mod (config.lua IDIOMA, padrao ingles), 1 = English, 2 = Portugues (Brasil)
    float escala = 1.f;
} cfg;

std::wstring pasta_mod, arq_camera, arq_estado, arq_sinal;
Valor camera, estado;
FILETIME mt_camera{}, mt_estado{};
std::vector<Categoria> categorias;
int categoria_atual = 1;
std::string idioma_mod = "en";

// idioma da interface: ingles por padrao, portugues se escolhido (ou se o mod estiver em pt-BR)
bool em_pt() { return cfg.idioma == 2 || (cfg.idioma == 0 && idioma_mod == "pt-BR"); }
const char *TR(const char *en, const char *pt) { return em_pt() ? pt : en; }
ULONGLONG ultimo_sinal = 0;

const ImU32 CORES[] = {
    IM_COL32(255, 210, 63, 255), IM_COL32(76, 201, 240, 255), IM_COL32(247, 37, 133, 255), IM_COL32(128, 237, 153, 255),
    IM_COL32(255, 159, 28, 255), IM_COL32(179, 136, 255, 255), IM_COL32(255, 89, 94, 255), IM_COL32(46, 196, 182, 255),
    IM_COL32(244, 162, 97, 255), IM_COL32(233, 255, 112, 255), IM_COL32(144, 224, 239, 255), IM_COL32(255, 175, 204, 255) };
ImU32 cor(int i) { return CORES[(std::max(1, i) - 1) % (sizeof(CORES) / sizeof(CORES[0]))]; }
const ImU32 PRETO = IM_COL32(0, 0, 0, 220);

bool revelada(int i)
{
    return cfg.ocultas.find("," + std::to_string(i) + ",") == std::string::npos;
}

void definir_revelada(int i, bool sim)
{
    const std::string k = "," + std::to_string(i) + ",";
    const size_t p = cfg.ocultas.find(k);
    if (sim && p != std::string::npos) cfg.ocultas.erase(p, k.size() - 1);
    else if (!sim && p == std::string::npos) cfg.ocultas += std::to_string(i) + ",";
}

// ajuste de distancia da categoria no ReShade: -1 = sem ajuste (segue o mod)
int ajuste_distancia(int i)
{
    const std::string k = std::to_string(i) + "=";
    size_t p = 0;
    while ((p = cfg.distancias.find(k, p)) != std::string::npos)
    {
        if (p == 0 || cfg.distancias[p - 1] == ';')
            return atoi(cfg.distancias.c_str() + p + k.size());
        p += k.size();
    }
    return -1;
}

void definir_ajuste_distancia(int i, int metros)
{
    std::string novo;
    size_t p = 0;
    while (p < cfg.distancias.size())
    {
        size_t f = cfg.distancias.find(';', p);
        if (f == std::string::npos) f = cfg.distancias.size();
        std::string par = cfg.distancias.substr(p, f - p);
        if (!par.empty() && atoi(par.c_str()) != i) novo += par + ";";
        p = f + 1;
    }
    if (metros >= 0) novo += std::to_string(i) + "=" + std::to_string(metros) + ";";
    cfg.distancias = novo;
}

// distancia de exibicao em uso (m); 0 = sem limite
double limite(const Categoria &c)
{
    const int a = ajuste_distancia(c.i);
    return a >= 0 ? double(a) : c.dist;
}

ImVec4 cor4(int i)
{
    const ImU32 c = cor(i);
    return ImVec4((c & 0xFF) / 255.f, ((c >> 8) & 0xFF) / 255.f, ((c >> 16) & 0xFF) / 255.f, 1.f);
}

void definir_caminhos(HMODULE modulo)
{
    wchar_t buf[MAX_PATH * 2];
    GetModuleFileNameW(modulo, buf, ARRAYSIZE(buf));
    std::wstring dir(buf);
    dir = dir.substr(0, dir.find_last_of(L"\\/"));
    pasta_mod = dir + L"\\ue4ss\\Mods\\RevelaZunidores";
    arq_camera = pasta_mod + L"\\camera.json";
    arq_estado = pasta_mod + L"\\estado.json";
    arq_sinal = pasta_mod + L"\\reshade_ativo.txt";
}

void carregar_config()
{
    using reshade::get_config_value;
    get_config_value(nullptr, "RevelaZunidores", "Ativo", cfg.ativo);
    get_config_value(nullptr, "RevelaZunidores", "Marcadores", cfg.marcadores);
    get_config_value(nullptr, "RevelaZunidores", "Nomes", cfg.nomes);
    get_config_value(nullptr, "RevelaZunidores", "Seta", cfg.seta);
    get_config_value(nullptr, "RevelaZunidores", "Bussola", cfg.bussola);
    get_config_value(nullptr, "RevelaZunidores", "EsconderOcultos", cfg.esconder_ocultos);
    get_config_value(nullptr, "RevelaZunidores", "MaxMarcadores", cfg.max_marcadores);
    char buf[512]; size_t tam = sizeof(buf) - 1;
    if (reshade::get_config_value(nullptr, "RevelaZunidores", "CategoriasOcultas", buf, &tam)) { buf[std::min(tam, sizeof(buf) - 1)] = 0; cfg.ocultas = buf; }
    if (cfg.ocultas.empty() || cfg.ocultas.front() != ',') cfg.ocultas = "," + cfg.ocultas;
    get_config_value(nullptr, "RevelaZunidores", "Idioma", cfg.idioma);
    char bufd[1024]; size_t tamd = sizeof(bufd) - 1;
    if (reshade::get_config_value(nullptr, "RevelaZunidores", "Distancias", bufd, &tamd)) { bufd[std::min(tamd, sizeof(bufd) - 1)] = 0; cfg.distancias = bufd; }
    get_config_value(nullptr, "RevelaZunidores", "Escala", cfg.escala);
}

void salvar_config()
{
    using reshade::set_config_value;
    set_config_value(nullptr, "RevelaZunidores", "Ativo", cfg.ativo);
    set_config_value(nullptr, "RevelaZunidores", "Marcadores", cfg.marcadores);
    set_config_value(nullptr, "RevelaZunidores", "Nomes", cfg.nomes);
    set_config_value(nullptr, "RevelaZunidores", "Seta", cfg.seta);
    set_config_value(nullptr, "RevelaZunidores", "Bussola", cfg.bussola);
    set_config_value(nullptr, "RevelaZunidores", "EsconderOcultos", cfg.esconder_ocultos);
    set_config_value(nullptr, "RevelaZunidores", "MaxMarcadores", cfg.max_marcadores);
    set_config_value(nullptr, "RevelaZunidores", "CategoriasOcultas", cfg.ocultas.c_str());
    set_config_value(nullptr, "RevelaZunidores", "Distancias", cfg.distancias.c_str());
    set_config_value(nullptr, "RevelaZunidores", "Idioma", cfg.idioma);
    set_config_value(nullptr, "RevelaZunidores", "Escala", cfg.escala);
}

void atualizar_dados()
{
    ler_json(arq_camera, camera, mt_camera);
    if (ler_json(arq_estado, estado, mt_estado))
    {
        categorias.clear();
        categoria_atual = int(estado.num("categoria_atual", 1));
        idioma_mod = estado.txt("idioma");
        if (idioma_mod.empty()) idioma_mod = "en";
        if (const Valor *cs = estado.campo("categorias"); cs && cs->t == Valor::Lista)
            for (const Valor &c : cs->a)
            {
                // sem "dist" no estado (mod antigo): 500 m, nunca "sem limite" (pesa no Limbo)
                Categoria cat{ int(c.num("i")), c.txt("nome"), c.txt("conteudo"), 0, c.num("dist", 500), {} };
                if (const Valor *its = c.campo("itens"); its && its->t == Valor::Lista)
                    for (const Valor &it : its->a)
                        cat.itens.push_back({ it.txt("n"), it.num("x"), it.num("y"), it.num("z"), it.boo("h") });
                cat.total = int(c.num("total", double(cat.itens.size())));
                cat.nome_en = c.txt("nome_en");
                cat.nome_pt = c.txt("nome_pt");
                categorias.push_back(std::move(cat));
            }
    }
}

// sinaliza para a janela Python que a camada do ReShade esta ativa (ela pausa a propria camada)
void enviar_sinal()
{
    ULONGLONG agora = GetTickCount64();
    if (agora - ultimo_sinal < 1000) return;
    ultimo_sinal = agora;
    HANDLE h = CreateFileW(arq_sinal.c_str(), GENERIC_WRITE, FILE_SHARE_READ | FILE_SHARE_DELETE, nullptr, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (h == INVALID_HANDLE_VALUE) return;
    char txt[64];
    int n = snprintf(txt, sizeof(txt), "%llu\n", agora);
    DWORD escritos = 0;
    WriteFile(h, txt, DWORD(n), &escritos, nullptr);
    CloseHandle(h);
}

// ---------------------------------------------------------------------------
// projecao (Unreal: X frente, Y direita, Z cima; FOV horizontal)
// ---------------------------------------------------------------------------
struct Cam
{
    double x, y, z, yaw, tanf;
    double f[3], r[3], u[3];

    explicit Cam(const Valor &d)
    {
        const double rad = 3.14159265358979 / 180.0;
        x = d.num("x"); y = d.num("y"); z = d.num("z"); yaw = d.num("yaw");
        double p = d.num("pitch") * rad, w = yaw * rad, ro = d.num("roll") * rad;
        double sp = sin(p), cp = cos(p), sy = sin(w), cy = cos(w), sr = sin(ro), cr = cos(ro);
        f[0] = cp * cy; f[1] = cp * sy; f[2] = sp;
        r[0] = sr * sp * cy - cr * sy; r[1] = sr * sp * sy + cr * cy; r[2] = -sr * cp;
        u[0] = -(cr * sp * cy + sr * sy); u[1] = cy * sr - cr * sp * sy; u[2] = cr * cp;
        double fov = std::clamp(d.num("fov", 90), 10.0, 170.0);
        tanf = tan(fov * rad / 2);
    }
    void local(double px, double py, double pz, double &lf, double &lr, double &lu) const
    {
        double dx = px - x, dy = py - y, dz = pz - z;
        lf = dx * f[0] + dy * f[1] + dz * f[2];
        lr = dx * r[0] + dy * r[1] + dz * r[2];
        lu = dx * u[0] + dy * u[1] + dz * u[2];
    }
    bool projetar(double px, double py, double pz, float w, float h, ImVec2 &out) const
    {
        double lf, lr, lu;
        local(px, py, pz, lf, lr, lu);
        if (lf <= 1) return false;
        double k = (w / 2) / tanf;
        out = ImVec2(float(w / 2 + lr / lf * k), float(h / 2 - lu / lf * k));
        return true;
    }
    double dist(double px, double py, double pz) const { return sqrt((px - x) * (px - x) + (py - y) * (py - y) + (pz - z) * (pz - z)) / 100; }
    double rumo(double px, double py) const
    {
        double a = atan2(py - y, px - x) * 180.0 / 3.14159265358979 - yaw;
        return fmod(a + 540.0, 360.0) - 180.0;
    }
};

void texto_contorno(ImDrawList *dl, ImVec2 p, ImU32 c, const char *t, float tamanho)
{
    ImFont *fonte = ImGui::GetFont();
    for (int dx = -1; dx <= 1; ++dx)
        for (int dy = -1; dy <= 1; ++dy)
            if (dx || dy) dl->AddText(fonte, tamanho, ImVec2(p.x + dx, p.y + dy), PRETO, t, nullptr, 0.f, nullptr);
    dl->AddText(fonte, tamanho, p, c, t, nullptr, 0.f, nullptr);
}

struct Alvo { const Item *it; double d; int cat; };

void desenhar(reshade::api::effect_runtime *runtime)
{
    // atalho Ctrl+Shift+I
    if (runtime->is_key_down(VK_CONTROL) && runtime->is_key_down(VK_SHIFT) && runtime->is_key_pressed('I'))
    {
        cfg.ativo = !cfg.ativo;
        salvar_config();
    }
    if (!cfg.ativo) return;

    atualizar_dados();
    if (camera.t != Valor::Obj || idade_arquivo(arq_camera) > 2.0) return; // jogo pausado/menu/mod parado
    enviar_sinal();

    const ImVec2 tela = ImGui::GetIO().DisplaySize;
    const float W = tela.x, H = tela.y;
    const float esc = std::clamp(cfg.escala, 0.5f, 3.f);
    const float fonte = ImGui::GetFontSize() * esc;
    ImDrawList *dl = ImGui::GetBackgroundDrawList(nullptr);
    Cam cam(camera);

    std::vector<Alvo> lista;
    const Alvo *alvo = nullptr;
    for (const Categoria &c : categorias)
    {
        if (!revelada(c.i)) continue; // categorias escolhidas na aba do add-on
        for (const Item &it : c.itens)
        {
            if (cfg.esconder_ocultos && it.oculto) continue;
            double d = cam.dist(it.x, it.y, it.z);
            const double lim = limite(c);
            if (lim > 0 && d > lim) continue; // distancia de exibicao da categoria
            lista.push_back({ &it, d, c.i });
        }
    }
    std::sort(lista.begin(), lista.end(), [](const Alvo &a, const Alvo &b) { return a.d < b.d; });
    if (!lista.empty()) alvo = &lista.front(); // mais proximo entre as categorias reveladas

    char rotulo[160];
    if (cfg.marcadores)
    {
        // limite POR CATEGORIA: uma categoria com muitos itens perto (ex.: 432 macas)
        // nao pode esconder as outras categorias marcadas
        std::map<int, int> por_cat;
        for (const Alvo &a : lista)
        {
            int &n = por_cat[a.cat];
            if (n >= cfg.max_marcadores) continue;
            ImVec2 s;
            if (!cam.projetar(a.it->x, a.it->y, a.it->z, W, H, s) || s.x < -20 || s.x > W + 20 || s.y < -20 || s.y > H + 20) continue;
            ++n;
            ImU32 c = cor(std::abs(a.cat));
            float t = float(std::clamp(13.0 - a.d / 25.0, 5.0, 13.0)) * esc;
            ImVec2 pts[4] = { { s.x, s.y - t }, { s.x + t, s.y }, { s.x, s.y + t }, { s.x - t, s.y } };
            dl->AddConvexPolyFilled(pts, 4, c);
            dl->AddPolyline(pts, 4, PRETO, ImDrawFlags_Closed, 2.f);
            if (cfg.nomes) snprintf(rotulo, sizeof(rotulo), "%s  %.0f m", a.it->nome.c_str(), a.d);
            else snprintf(rotulo, sizeof(rotulo), "%.0f m", a.d);
            ImVec2 tam = ImGui::CalcTextSize(rotulo);
            tam.x *= esc; tam.y *= esc;
            texto_contorno(dl, ImVec2(s.x - tam.x / 2, s.y - t - tam.y - 2), c, rotulo, fonte);
        }
    }

    if (cfg.seta && alvo)
    {
        ImVec2 s;
        const float margem = 60 * esc;
        bool na_tela = cam.projetar(alvo->it->x, alvo->it->y, alvo->it->z, W, H, s) &&
                       s.x > margem && s.x < W - margem && s.y > margem && s.y < H - margem;
        if (!na_tela)
        {
            double lf, lr, lu;
            cam.local(alvo->it->x, alvo->it->y, alvo->it->z, lf, lr, lu);
            double vx = lr, vy = -lu;
            if (lf <= 1 && std::abs(vx) < 1e-3) vx = 1;
            double n = std::max(1e-6, sqrt(vx * vx + vy * vy));
            vx /= n; vy /= n;
            double rx = W / 2 - margem, ry = H / 2 - margem;
            double k = 1 / sqrt((vx / rx) * (vx / rx) + (vy / ry) * (vy / ry));
            float px = float(W / 2 + vx * k), py = float(H / 2 + vy * k);
            float ang = float(atan2(vy, vx));
            ImU32 c = cor(alvo->cat);
            ImVec2 pts[4];
            const float da[4] = { 0.f, 2.5f, 3.14159f, -2.5f }, raio[4] = { 26.f, 14.f, 6.f, 14.f };
            for (int i = 0; i < 4; ++i) pts[i] = ImVec2(px + raio[i] * esc * cosf(ang + da[i]), py + raio[i] * esc * sinf(ang + da[i]));
            dl->AddTriangleFilled(pts[0], pts[1], pts[2], c);
            dl->AddTriangleFilled(pts[0], pts[2], pts[3], c);
            dl->AddPolyline(pts, 4, PRETO, ImDrawFlags_Closed, 2.f);
            snprintf(rotulo, sizeof(rotulo), "%.0f m", alvo->d);
            ImVec2 tam = ImGui::CalcTextSize(rotulo);
            texto_contorno(dl, ImVec2(px - float(vx) * 40 * esc - tam.x * esc / 2, py - float(vy) * 40 * esc - tam.y * esc / 2), c, rotulo, fonte * 1.15f);
        }
    }

    if (cfg.bussola)
    {
        const float larg = std::min(700.f * esc, W * 0.45f);
        const float x0 = W / 2 - larg / 2, x1 = W / 2 + larg / 2, yb = 34 * esc;
        const ImU32 cinza = IM_COL32(200, 200, 200, 230);
        dl->AddLine(ImVec2(x0, yb), ImVec2(x1, yb), PRETO, 4.f);
        dl->AddLine(ImVec2(x0, yb), ImVec2(x1, yb), cinza, 2.f);
        for (int a = -90; a <= 90; a += 15)
        {
            float xx = W / 2 + a / 90.f * larg / 2;
            dl->AddLine(ImVec2(xx, yb - (a % 45 == 0 ? 6 : 3) * esc), ImVec2(xx, yb), cinza, 1.f);
        }
        texto_contorno(dl, ImVec2(W / 2 - 4 * esc, yb - 20 * esc), IM_COL32_WHITE, "v", fonte);
        std::map<int, int> por_cat; // ate 20 pontos por categoria na bussola
        for (const Alvo &a : lista)
        {
            if (por_cat[a.cat]++ >= 20) continue;
            double ru = cam.rumo(a.it->x, a.it->y);
            if (std::abs(ru) > 90) continue;
            float xx = float(W / 2 + ru / 90 * larg / 2);
            bool eh_alvo = alvo && a.it == alvo->it;
            float r = (eh_alvo ? 6.f : 3.f) * esc;
            dl->AddCircleFilled(ImVec2(xx, yb + 4 * esc + r), r + 1, PRETO, 0);
            dl->AddCircleFilled(ImVec2(xx, yb + 4 * esc + r), r, cor(std::abs(a.cat)), 0);
            if (eh_alvo)
            {
                snprintf(rotulo, sizeof(rotulo), "%.0f m", a.d);
                ImVec2 tam = ImGui::CalcTextSize(rotulo);
                texto_contorno(dl, ImVec2(xx - tam.x * esc / 2, yb + 18 * esc), cor(alvo->cat), rotulo, fonte);
            }
        }
        if (alvo)
        {
            double ru = cam.rumo(alvo->it->x, alvo->it->y);
            if (std::abs(ru) > 90)
                texto_contorno(dl, ImVec2(ru > 0 ? x1 + 10 * esc : x0 - 22 * esc, yb - 10 * esc), cor(alvo->cat), ru > 0 ? ">>" : "<<", fonte * 1.2f);
        }
    }
}

// nome da categoria no idioma da interface (o mod envia os dois)
const std::string &nome_cat(const Categoria &c)
{
    const std::string &n = em_pt() ? c.nome_pt : c.nome_en;
    return n.empty() ? c.nome : n;
}

// aba de configuracoes em ReShade > Add-ons
void configuracoes(reshade::api::effect_runtime *)
{
    bool mudou = false;
    char rotulo[256];
    mudou |= ImGui::Checkbox(TR("Enable reveal (Ctrl+Shift+I)###ativo", "Ativar revelacao (Ctrl+Shift+I)###ativo"), &cfg.ativo);

    if (ImGui::CollapsingHeader(TR("Reveal methods###metodos", "Metodos de revelacao###metodos"), ImGuiTreeNodeFlags_DefaultOpen))
    {
        mudou |= ImGui::Checkbox(TR("Item markers (through walls)###marc", "Marcadores nos itens (atraves das paredes)###marc"), &cfg.marcadores);
        mudou |= ImGui::Checkbox(TR("Show actor name on marker###nomes", "Mostrar nome do ator no marcador###nomes"), &cfg.nomes);
        mudou |= ImGui::Checkbox(TR("Screen-edge arrow to the nearest###seta", "Seta na borda para o mais proximo###seta"), &cfg.seta);
        mudou |= ImGui::Checkbox(TR("Compass at the top###bussola", "Bussola no topo###bussola"), &cfg.bussola);
        mudou |= ImGui::SliderInt(TR("Max. markers per category###maxm", "Max. de marcadores por categoria###maxm"), &cfg.max_marcadores, 1, 300);
        mudou |= ImGui::SliderFloat(TR("Scale###esc", "Escala###esc"), &cfg.escala, 0.5f, 3.f, "%.2f");
    }

    if (ImGui::CollapsingHeader(TR("Revealed categories###cats", "Categorias reveladas###cats"), ImGuiTreeNodeFlags_DefaultOpen))
    {
        ImGui::TextDisabled("%s", TR("Each collectible type is toggled separately (independent of F5/meter).",
                                     "Cada tipo de coletavel liga/desliga separadamente (independe do F5/medidor)."));
        if (categorias.empty())
            ImGui::TextDisabled("%s", TR("Waiting for estado.json from the Lua mod...", "Aguardando estado.json do mod Lua..."));
        for (const Categoria &c : categorias)
        {
            ImGui::PushID(c.i);
            ImGui::ColorButton("##cor", cor4(c.i), ImGuiColorEditFlags_NoTooltip | ImGuiColorEditFlags_NoPicker, ImVec2(14, 14));
            ImGui::SameLine();
            bool v = revelada(c.i);
            snprintf(rotulo, sizeof(rotulo), TR("%s  [%s]  (%d on map)###rev", "%s  [%s]  (%d no mapa)###rev"),
                     nome_cat(c).c_str(), c.conteudo.c_str(), c.total);
            if (ImGui::Checkbox(rotulo, &v)) { definir_revelada(c.i, v); mudou = true; }
            ImGui::Indent(22.f);
            int aj = ajuste_distancia(c.i);
            char fmt[96];
            const std::string do_mod = c.dist > 0 ? std::to_string(int(c.dist)) + " m" : TR("no limit", "sem limite");
            if (aj < 0) snprintf(fmt, sizeof(fmt), TR("follow mod (%s)", "segue o mod (%s)"), do_mod.c_str());
            else if (aj == 0) snprintf(fmt, sizeof(fmt), "%s", TR("no limit", "sem limite"));
            else snprintf(fmt, sizeof(fmt), "%%d m");
            ImGui::SetNextItemWidth(220.f);
            if (ImGui::SliderInt(TR("distance###d", "distancia###d"), &aj, -1, 1000, fmt, ImGuiSliderFlags_AlwaysClamp))
            {
                definir_ajuste_distancia(c.i, aj);
                mudou = true;
            }
            ImGui::Unindent(22.f);
            ImGui::PopID();
        }
        if (ImGui::SmallButton(TR("Check all###todas", "Marcar todas###todas"))) { cfg.ocultas = ","; mudou = true; }
        ImGui::SameLine();
        if (ImGui::SmallButton(TR("Uncheck all###nenhuma", "Desmarcar todas###nenhuma")))
        {
            for (const Categoria &c : categorias) definir_revelada(c.i, false);
            mudou = true;
        }
        ImGui::SameLine();
        if (ImGui::SmallButton(TR("Only the meter/F5 one###so", "So a do medidor/F5###so")))
        {
            for (const Categoria &c : categorias) definir_revelada(c.i, c.i == categoria_atual);
            mudou = true;
        }
        ImGui::TextDisabled("%s", TR("Display distance (drag to the far left = follow the mod; 0 = no limit):",
                                     "Distancia de exibicao (arraste ate o fim esquerdo = seguir o mod; 0 = sem limite):"));
        const int rapidos[] = { -1, 50, 100, 150, 300, 0 };
        const char *nomes[] = { TR("All: from mod###r0", "Todas: do mod###r0"), "50 m###r1", "100 m###r2", "150 m###r3", "300 m###r4",
                                TR("No limit###r5", "Sem limite###r5") };
        for (int k = 0; k < 6; ++k)
        {
            if (k) ImGui::SameLine();
            if (ImGui::SmallButton(nomes[k]))
            {
                for (const Categoria &c : categorias) definir_ajuste_distancia(c.i, rapidos[k]);
                mudou = true;
            }
        }
    }

    if (ImGui::CollapsingHeader(TR("Reveal filter###filtro", "Filtro da revelacao###filtro")))
    {
        mudou |= ImGui::Checkbox(TR("Don't reveal hidden items###ocultos", "Nao revelar itens ocultos###ocultos"), &cfg.esconder_ocultos);
    }

    if (ImGui::CollapsingHeader("Language / Idioma###idioma"))
    {
        mudou |= ImGui::RadioButton("Follow mod / Segue o mod###l0", &cfg.idioma, 0);
        ImGui::SameLine();
        mudou |= ImGui::RadioButton("English###l1", &cfg.idioma, 1);
        ImGui::SameLine();
        mudou |= ImGui::RadioButton("Portugues (Brasil)###l2", &cfg.idioma, 2);
        ImGui::TextDisabled(TR("Mod language: %s", "Idioma do mod: %s"), idioma_mod.c_str());
    }
    if (mudou) salvar_config();

    if (ImGui::CollapsingHeader(TR("Status###estado", "Estado###estado")))
    {
        double idade = idade_arquivo(arq_camera);
        int total = 0, rev = 0;
        for (const auto &c : categorias) { total += c.total; if (revelada(c.i)) rev += c.total; }
        if (idade > 1e8) ImGui::TextDisabled("%s", TR("camera.json not found - is the Lua mod running?", "camera.json nao encontrado - o mod Lua esta rodando?"));
        else ImGui::TextDisabled(TR("camera.json: %.1f s ago | %d items on map | %d revealed", "camera.json: %.1f s atras | %d itens no mapa | %d revelados"), idade, total, rev);
    }
}
} // namespace

BOOL APIENTRY DllMain(HMODULE modulo, DWORD motivo, LPVOID)
{
    switch (motivo)
    {
    case DLL_PROCESS_ATTACH:
        if (!reshade::register_addon(modulo)) return FALSE;
        definir_caminhos(modulo);
        carregar_config();
        reshade::register_event<reshade::addon_event::reshade_overlay>(desenhar);
        reshade::register_overlay(nullptr, configuracoes);
        break;
    case DLL_PROCESS_DETACH:
        reshade::unregister_overlay(nullptr, configuracoes);
        reshade::unregister_event<reshade::addon_event::reshade_overlay>(desenhar);
        reshade::unregister_addon(modulo);
        break;
    }
    return TRUE;
}
