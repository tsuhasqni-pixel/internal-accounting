using System.Diagnostics;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;

namespace InternalAccountingWindows;

internal static class Program
{
    [STAThread]
    private static void Main()
    {
        ApplicationConfiguration.Initialize();
        Application.Run(new MainWindow());
    }
}

internal sealed class MainWindow : Form
{
    private const string Host = "internal-accounting.app";
    private readonly WebView2 view = new() { Dock = DockStyle.Fill };

    public MainWindow()
    {
        Text = "内部管理会計";
        StartPosition = FormStartPosition.CenterScreen;
        ClientSize = new Size(1120, 740);
        MinimumSize = new Size(860, 600);
        Controls.Add(view);
    }

    protected override async void OnShown(EventArgs e)
    {
        base.OnShown(e);
        try
        {
            var docs = Path.Combine(AppContext.BaseDirectory, "docs");
            if (!File.Exists(Path.Combine(docs, "index.html")))
                throw new FileNotFoundException("画面ファイルがありません。", Path.Combine(docs, "index.html"));

            var profile = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "TsuhaTools", "InternalAccounting", "WebView2");
            Directory.CreateDirectory(profile);
            var environment = await CoreWebView2Environment.CreateAsync(userDataFolder: profile);
            await view.EnsureCoreWebView2Async(environment);
            view.CoreWebView2.SetVirtualHostNameToFolderMapping(
                Host, docs, CoreWebView2HostResourceAccessKind.DenyCors);
            view.CoreWebView2.NavigationStarting += (_, args) =>
            {
                if (args.Uri.StartsWith($"https://{Host}/", StringComparison.OrdinalIgnoreCase))
                    return;
                args.Cancel = true;
                if (Uri.TryCreate(args.Uri, UriKind.Absolute, out var uri) &&
                    (uri.Scheme == "https" || uri.Scheme == "http"))
                {
                    try { Process.Start(new ProcessStartInfo(uri.AbsoluteUri) { UseShellExecute = true }); }
                    catch { /* External links must not stop the local app. */ }
                }
            };
            view.CoreWebView2.Settings.AreDevToolsEnabled = false;
            view.CoreWebView2.Navigate($"https://{Host}/index.html");
        }
        catch (Exception ex)
        {
            MessageBox.Show(this,
                "アプリの起動に失敗しました。Microsoft Edge WebView2 Runtime の有無を確認してください。\n\n" +
                ex.Message, "起動エラー", MessageBoxButtons.OK, MessageBoxIcon.Error);
            Close();
        }
    }
}
