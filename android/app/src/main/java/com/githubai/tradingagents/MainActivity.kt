package com.githubai.tradingagents

import android.app.Activity
import android.os.Bundle
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.view.Gravity
import android.widget.*
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import kotlin.concurrent.thread

class MainActivity : Activity() {
    private val navy = Color.rgb(7, 13, 25)
    private val panel = Color.rgb(17, 27, 44)
    private val teal = Color.rgb(45, 212, 191)
    private val muted = Color.rgb(156, 174, 194)
    private lateinit var api: EditText
    private lateinit var ticker: EditText
    private lateinit var status: TextView
    private lateinit var result: TextView
    private lateinit var runButton: TextView
    private lateinit var healthButton: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.statusBarColor = navy
        window.navigationBarColor = navy
        val prefs = getSharedPreferences("tradingagents_mobile", MODE_PRIVATE)
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(18), dp(14), dp(18), dp(14))
            setBackgroundColor(navy)
        }
        val scroll = ScrollView(this)
        val col = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        scroll.addView(col)

        val brandRow = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL }
        val logo = TextView(this).apply {
            text = "AI"; textSize = 18f; setTypeface(null, Typeface.BOLD); setTextColor(navy)
            gravity = Gravity.CENTER; background = rounded(teal, 14)
            layoutParams = LinearLayout.LayoutParams(dp(48), dp(48))
        }
        brandRow.addView(logo)
        val brandText = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(dp(12), 0, 0, 0) }
        brandText.addView(label("AI TRADING", 23f, Color.WHITE, true))
        brandText.addView(label("MULTI-AGENT RESEARCH", 11f, teal, true))
        brandRow.addView(brandText, LinearLayout.LayoutParams(0, -2, 1f))
        brandRow.addView(label("SIGNAL ONLY", 10f, teal, true))
        col.addView(brandRow)
        col.addView(label("Research intelligence, not order execution.", 13f, muted, false).apply {
            setPadding(0, dp(8), 0, dp(16))
        })

        val statusCard = card()
        statusCard.addView(label("SYSTEM STATUS", 11f, muted, true))
        status = label("●  BACKEND NOT CHECKED", 14f, Color.YELLOW, true)
        statusCard.addView(status)
        statusCard.addView(label("No broker orders are placed by this app.", 12f, muted, false))
        col.addView(statusCard)

        val researchCard = card()
        researchCard.addView(label("AI RESEARCH", 16f, Color.WHITE, true))
        researchCard.addView(label("TradingAgents coordinates specialist analysts, researchers, a trader agent and risk reviewers.", 12f, muted, false))
        researchCard.addView(label("TICKER / SYMBOL", 11f, teal, true).apply { setPadding(0, dp(14), 0, dp(4)) })
        ticker = field("^NSEI", "e.g. NVDA, AAPL, ^NSEI")
        researchCard.addView(ticker)
        researchCard.addView(label("BACKEND HTTPS URL", 11f, teal, true).apply { setPadding(0, dp(12), 0, dp(4)) })
        api = field(prefs.getString("backend_url", "") ?: "", "https://your-deployed-backend.example.com")
        researchCard.addView(api)
        healthButton = actionButton("CHECK CONNECTION", false) { checkHealth() }
        researchCard.addView(healthButton)
        runButton = actionButton("RUN AI RESEARCH", true) { runAnalysis() }
        val runParams = LinearLayout.LayoutParams(-1, dp(50)); runParams.topMargin = dp(10)
        researchCard.addView(runButton, runParams)
        col.addView(researchCard)

        val reportCard = card()
        reportCard.addView(label("RESEARCH REPORT", 16f, Color.WHITE, true))
        result = label("Enter a ticker and connect a deployed backend. The app will show the real backend response; it will not invent prices or signals.", 13f, muted, false)
        result.setTextIsSelectable(true)
        reportCard.addView(result)
        col.addView(reportCard)
        col.addView(label("DATA & SAFETY", 11f, teal, true).apply { setPadding(0, dp(16), 0, dp(4)) })
        col.addView(label("• API keys stay on the backend\n• Backend errors produce no recommendation\n• Research output is not guaranteed to be profitable\n• No broker credentials or order-placement code in the APK", 12f, muted, false))
        root.addView(scroll, LinearLayout.LayoutParams(-1, 0, 1f))
        root.addView(label("AI TRADING  •  RESEARCH WORKSPACE", 10f, muted, true).apply {
            gravity = Gravity.CENTER; setPadding(0, dp(12), 0, 0)
        })
        setContentView(root)
    }

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()
    private fun rounded(color: Int, radius: Int): GradientDrawable =
        GradientDrawable().apply { setColor(color); cornerRadius = dp(radius).toFloat() }

    private fun card(): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        setPadding(dp(16), dp(14), dp(16), dp(16))
        background = rounded(panel, 18)
        layoutParams = LinearLayout.LayoutParams(-1, -2).apply { bottomMargin = dp(12) }
    }

    private fun label(s: String, size: Float, color: Int, bold: Boolean): TextView =
        TextView(this).apply {
            text = s; textSize = size; setTextColor(color)
            if (bold) setTypeface(null, Typeface.BOLD)
            setPadding(0, dp(4), 0, dp(4))
        }

    private fun field(value: String, hintText: String) = EditText(this).apply {
        setText(value); hint = hintText; setTextColor(Color.WHITE); setHintTextColor(muted)
        textSize = 14f; setSingleLine(true); setPadding(dp(12), dp(8), dp(12), dp(8))
        background = rounded(Color.rgb(9, 17, 31), 10)
    }

    private fun actionButton(textValue: String, primary: Boolean, action: () -> Unit): TextView =
        TextView(this).apply {
            text = textValue; textSize = 13f; setTypeface(null, Typeface.BOLD); gravity = Gravity.CENTER
            setTextColor(if (primary) navy else teal)
            background = rounded(if (primary) teal else Color.rgb(25, 46, 63), 12)
            isClickable = true; isFocusable = true; setOnClickListener { action() }
            layoutParams = LinearLayout.LayoutParams(-1, dp(46)).apply { topMargin = dp(10) }
        }

    private fun endpoint(path: String): String {
        val base = api.text.toString().trim().trimEnd('/')
        require(base.startsWith("https://")) { "Enter your deployed HTTPS backend URL first." }
        getSharedPreferences("tradingagents_mobile", MODE_PRIVATE).edit().putString("backend_url", base).apply()
        return base + path
    }

    private fun request(path: String, body: String? = null): JSONObject {
        val c = URL(endpoint(path)).openConnection() as HttpURLConnection
        c.requestMethod = if (body == null) "GET" else "POST"
        c.connectTimeout = 10000; c.readTimeout = 260000
        c.setRequestProperty("Accept", "application/json")
        if (body != null) {
            c.doOutput = true; c.setRequestProperty("Content-Type", "application/json")
            c.outputStream.use { it.write(body.toByteArray(Charsets.UTF_8)) }
        }
        val code = c.responseCode
        val stream = if (code in 200..299) c.inputStream else c.errorStream
        val data = stream?.bufferedReader()?.use { it.readText() } ?: "{}"
        c.disconnect()
        if (code !in 200..299) error("Backend HTTP $code: $data")
        return JSONObject(data)
    }

    private fun busy(isBusy: Boolean, message: String) {
        runButton.isEnabled = !isBusy; healthButton.isEnabled = !isBusy
        runButton.alpha = if (isBusy) 0.55f else 1f
        status.text = message; status.setTextColor(if (isBusy) Color.YELLOW else teal)
    }

    private fun checkHealth() {
        busy(true, "●  CHECKING BACKEND…")
        thread {
            try {
                val d = request("/health")
                runOnUiThread {
                    val ready = d.optBoolean("analysis_ready", false)
                    val cli = d.optBoolean("framework_cli_available", false)
                    val provider = d.optBoolean("provider_configured", false)
                    status.text = if (ready) "●  BACKEND + AI CONFIGURED" else "●  API REACHABLE • SETUP INCOMPLETE"
                    status.setTextColor(if (ready) teal else Color.YELLOW)
                    result.text = "Health check\nService: " + d.optString("service", "TradingAgents API") +
                        "\nFramework CLI: " + (if (cli) "available" else "missing") +
                        "\nModel provider key: " + (if (provider) "configured" else "not detected") +
                        "\n\n" + d.optString("message", "Check backend environment variables before running research.")
                    runButton.isEnabled = true; healthButton.isEnabled = true; runButton.alpha = 1f
                }
            } catch (e: Exception) {
                runOnUiThread {
                    status.text = "●  BACKEND UNREACHABLE"; status.setTextColor(Color.RED)
                    result.text = "Connection failed\n" + e.message + "\n\nNo recommendation generated."
                    runButton.isEnabled = true; healthButton.isEnabled = true; runButton.alpha = 1f
                }
            }
        }
    }

    private fun runAnalysis() {
        val symbol = ticker.text.toString().trim()
        if (!symbol.matches(Regex("[A-Za-z0-9.^=\\-]{1,20}"))) {
            result.text = "Enter a valid ticker / symbol."; return
        }
        busy(true, "●  RESEARCH RUNNING…")
        result.text = "Running multi-agent research. This can take several minutes. No trade signal is assumed while research is incomplete."
        thread {
            try {
                val d = request("/v1/analyze", JSONObject().put("ticker", symbol).toString())
                val report = d.optString("report", "").trim()
                runOnUiThread {
                    status.text = if (d.optString("status") == "READY") "●  RESEARCH COMPLETE" else "●  RESEARCH UNAVAILABLE"
                    status.setTextColor(if (d.optString("status") == "READY") teal else Color.YELLOW)
                    result.text = "Status: " + d.optString("status", "UNKNOWN") +
                        "\nTicker: " + d.optString("ticker", symbol) +
                        "\nGenerated: " + d.optString("generated_at", "not supplied") +
                        "\n\n" + d.optString("summary", "") + "\n\n" +
                        if (report.isBlank()) "No report returned. Check provider/data-source configuration on the backend." else report
                    runButton.isEnabled = true; healthButton.isEnabled = true; runButton.alpha = 1f
                }
            } catch (e: Exception) {
                runOnUiThread {
                    status.text = "●  RESEARCH FAILED — NO SIGNAL"; status.setTextColor(Color.RED)
                    result.text = "Research unavailable\n" + e.message +
                        "\n\nNo recommendation generated. Check backend logs, provider credentials and market-data sources."
                    runButton.isEnabled = true; healthButton.isEnabled = true; runButton.alpha = 1f
                }
            }
        }
    }
}
