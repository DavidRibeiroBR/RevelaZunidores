// Teste da logica do add-on (JSON, projecao, carga de estado) sem o ReShade.
#include "../RevelaZunidores.cpp"
#include <cassert>

static void grava(const std::wstring &c, const char *t)
{
    FILE *f = _wfopen(c.c_str(), L"wb");
    fputs(t, f);
    fclose(f);
}

int main()
{
    int falhas = 0;
    auto confere = [&](bool ok, const char *o) { printf("%s %s\n", ok ? "OK  " : "FALHA", o); if (!ok) ++falhas; };

    wchar_t tmp[MAX_PATH];
    GetTempPathW(MAX_PATH, tmp);
    pasta_mod = std::wstring(tmp) + L"rz_teste";
    CreateDirectoryW(pasta_mod.c_str(), nullptr);
    arq_camera = pasta_mod + L"\\camera.json";
    arq_estado = pasta_mod + L"\\estado.json";

    grava(arq_camera, "{\"seq\":7,\"t\":1,\"x\":0.0,\"y\":0.0,\"z\":0.0,\"pitch\":0.000,\"yaw\":0.000,\"roll\":0.000,\"fov\":90.000}");
    grava(arq_estado,
        "{\"versao\":3,\"t\":1,\"jogador\":true,\"categoria_atual\":2,\"indicadores\":{\"contorno\":false,\"contorno_valor\":252,\"vibracao\":false,\"vibracao_dist\":15.0},"
        "\"categorias\":[{\"i\":1,\"nome\":\"Zunidores (Chirpers)\",\"conteudo\":\"Base\",\"referencia\":\"73\",\"itens\":[]},"
        "{\"i\":2,\"nome\":\"Corpos \\u0022falantes\\u0022\",\"conteudo\":\"Base\",\"referencia\":\"46\",\"itens\":["
        "{\"n\":\"BP_CorpseDialog_C_3\",\"c\":\"BP_CorpseDialog_C\",\"d\":10.0,\"ang\":0.0,\"dz\":0.0,\"x\":1000.0,\"y\":0.0,\"z\":0.0,\"h\":false},"
        "{\"n\":\"BP_CorpseDialog_C_9\",\"c\":\"BP_CorpseDialog_C\",\"d\":14.1,\"ang\":45.0,\"dz\":0.0,\"x\":1000.0,\"y\":1000.0,\"z\":-1.5e2,\"h\":true}]}]}");

    atualizar_dados();
    confere(camera.t == Valor::Obj && camera.num("seq") == 7, "camera.json lido");
    confere(categorias.size() == 2, "2 categorias");
    confere(categoria_atual == 2, "categoria_atual = 2");
    confere(categorias.size() == 2 && categorias[1].nome == "Corpos \"falantes\"", "escape \\u0022 decodificado");
    confere(categorias.size() == 2 && categorias[1].itens.size() == 2 && categorias[1].itens[1].oculto, "itens e flag oculto");
    confere(categorias.size() == 2 && categorias[1].itens.size() == 2 && categorias[1].itens[1].z == -150.0, "numero com expoente");

    // nao rele se o arquivo nao mudou
    categorias.clear();
    atualizar_dados();
    confere(categorias.empty(), "cache por data de modificacao");

    Cam c(camera);
    ImVec2 s;
    confere(c.projetar(1000, 0, 0, 1920, 1080, s) && fabs(s.x - 960) < 0.5 && fabs(s.y - 540) < 0.5, "item a frente no centro");
    confere(c.projetar(1000, 1000, 0, 1920, 1080, s) && fabs(s.x - 1920) < 0.5, "45 graus na borda direita (FOV 90)");
    confere(c.projetar(1000, 0, 300, 1920, 1080, s) && s.y < 540, "item acima aparece acima");
    confere(!c.projetar(-1000, 0, 0, 1920, 1080, s), "item atras nao projeta");
    confere(fabs(c.dist(1000, 0, 0) - 10.0) < 1e-9, "distancia em metros");
    confere(fabs(fabs(c.rumo(-1000, 1)) - 180) < 0.1, "rumo atras = 180");

    Valor cy; Leitor l{ "{\"x\":0,\"y\":0,\"z\":0,\"pitch\":0,\"yaw\":90,\"roll\":0,\"fov\":90}", nullptr };
    l.e = l.p + strlen(l.p);
    cy = l.valor();
    Cam c90(cy);
    confere(c90.projetar(0, 1000, 0, 1920, 1080, s) && fabs(s.x - 960) < 0.5, "yaw 90: item em +Y no centro");
    confere(fabs(c90.rumo(1000, 0) + 90) < 0.1, "yaw 90: item em +X a esquerda");

    // categorias reveladas por tipo
    confere(categorias.empty() || true, "");
    mt_estado = FILETIME{};
    atualizar_dados();
    confere(categorias.size() == 2 && categorias[1].total == 2 && categorias[1].conteudo == "Base", "total (sem campo) e conteudo");
    cfg.ocultas = ",";
    confere(revelada(1) && revelada(2), "todas reveladas por padrao");
    definir_revelada(2, false);
    confere(!revelada(2) && revelada(1) && cfg.ocultas == ",2,", "desmarcar categoria 2");
    definir_revelada(11, false);
    confere(!revelada(11) && !revelada(2) && revelada(1), "desmarcar 11 sem confundir com 1");
    definir_revelada(2, true);
    confere(revelada(2) && !revelada(11) && cfg.ocultas == ",11,", "remarcar categoria 2");
    definir_revelada(11, true);
    confere(cfg.ocultas == ",", "todas reveladas de novo");

    // distancia de exibicao por categoria
    {
        Categoria c1{ 1, "A", "", 0, 150.0, {} }, c11{ 11, "B", "", 0, 40.0, {} }, c0{ 2, "C", "", 0, 0.0, {} };
        cfg.distancias.clear();
        confere(ajuste_distancia(1) == -1 && limite(c1) == 150.0, "sem ajuste segue o mod (150)");
        confere(limite(c0) == 0.0, "mod sem limite (0)");
        definir_ajuste_distancia(11, 25);
        confere(ajuste_distancia(11) == 25 && ajuste_distancia(1) == -1 && limite(c11) == 25.0, "ajuste 11=25 sem afetar 1");
        definir_ajuste_distancia(1, 0);
        confere(limite(c1) == 0.0 && cfg.distancias == "11=25;1=0;", "ajuste 1 = sem limite");
        definir_ajuste_distancia(11, 300);
        confere(ajuste_distancia(11) == 300 && cfg.distancias == "1=0;11=300;", "trocar ajuste existente");
        definir_ajuste_distancia(1, -1);
        definir_ajuste_distancia(11, -1);
        confere(cfg.distancias.empty() && limite(c11) == 40.0, "voltar a seguir o mod");
    }
    mt_estado = FILETIME{};
    grava(arq_estado, "{\"categoria_atual\":1,\"categorias\":[{\"i\":7,\"nome\":\"Macas\",\"conteudo\":\"DLC2\",\"total\":3826,\"dist\":40.0,\"dist_cfg\":40.0,\"itens\":[]}]}");
    atualizar_dados();
    confere(categorias.size() == 1 && categorias[0].dist == 40.0 && categorias[0].total == 3826, "dist e total lidos do estado");

    // idioma: ingles por padrao, segue o mod, ou escolha propria
    mt_estado = FILETIME{};
    grava(arq_estado, "{\"idioma\":\"pt-BR\",\"categoria_atual\":1,\"categorias\":[{\"i\":1,\"nome\":\"Zunidores (Chirpers)\","
                      "\"nome_en\":\"Chirpers\",\"nome_pt\":\"Zunidores (Chirpers)\",\"total\":5,\"dist\":150,\"itens\":[]}]}");
    atualizar_dados();
    cfg.idioma = 0;
    confere(idioma_mod == "pt-BR" && em_pt() && nome_cat(categorias[0]) == "Zunidores (Chirpers)", "segue o mod em pt-BR");
    cfg.idioma = 1;
    confere(!em_pt() && nome_cat(categorias[0]) == "Chirpers" && std::string(TR("Scale", "Escala")) == "Scale", "forcado ingles");
    cfg.idioma = 2;
    confere(em_pt() && std::string(TR("Scale", "Escala")) == "Escala", "forcado portugues");
    mt_estado = FILETIME{};
    grava(arq_estado, "{\"categoria_atual\":1,\"categorias\":[{\"i\":1,\"nome\":\"Chirpers\",\"itens\":[]}]}");
    atualizar_dados();
    cfg.idioma = 0;
    confere(idioma_mod == "en" && !em_pt() && nome_cat(categorias[0]) == "Chirpers", "estado sem idioma = ingles");

    Leitor ruim{ "{\"a\":[1,2", nullptr };
    ruim.e = ruim.p + strlen(ruim.p);
    ruim.valor();
    confere(!ruim.ok, "JSON truncado e rejeitado");

    printf("%s (%d falhas)\n", falhas ? "TESTE FALHOU" : "TESTE OK", falhas);
    return falhas;
}
