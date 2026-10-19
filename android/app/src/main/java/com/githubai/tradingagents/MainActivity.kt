package com.githubai.tradingagents

import android.app.Activity
import android.os.Bundle
import android.graphics.Color
import android.view.ViewGroup
import android.widget.*
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import kotlin.concurrent.thread

class MainActivity : Activity() {
    private val navy = Color.rgb(13,23,42)
    private val teal = Color.rgb(45,212,191)
    private lateinit var api: EditText
    private lateinit var ticker: EditText
    private lateinit var status: TextView
    private lateinit var result: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.statusBarColor = navy
        window.navigationBarColor = navy
        val root = LinearLayout(this).apply { orientation = 1; setPadding(24,28,24,24); setBackgroundColor(navy) }
        val scroll = ScrollView(this)
        val col = LinearLayout(this).apply { orientation = 1 }
        col.addView(text("TRADINGAGENTS",26f,teal))
        col.addView(text("Multi-agent market research • Signal-only",14f,Color.LTGRAY))
        api = field("Backend HTTPS URL", "https://your-backend.example.com")
        ticker = field("Ticker", "AAPL")
        col.addView(text("BACKEND URL",12f,teal)); col.addView(api)
        col.addView(text("SYMBOL / TICKER",12f,teal)); col.addView(ticker)
        col.addView(button("CHECK BACKEND") { checkHealth() })
        status = text("Backend not checked",14f,Color.YELLOW); col.addView(status)
        col.addView(button("RUN RESEARCH") { runAnalysis() })
        result = text("Choose a ticker and run research. No orders are placed.",15f,Color.WHITE); col.addView(result)
        col.addView(text("Research only — not financial advice. Keep API keys on the backend.",12f,Color.LTGRAY))
        scroll.addView(col)
        root.addView(scroll,LinearLayout.LayoutParams(-1,0,1f))
        setContentView(root)
    }

    private fun text(s:String,size:Float,color:Int) = TextView(this).apply {
        text=s; textSize=size; setTextColor(color); setPadding(0,10,0,10)
    }
    private fun field(h:String,v:String) = EditText(this).apply {
        hint=h; setText(v); setTextColor(Color.WHITE); setHintTextColor(Color.GRAY); textSize=15f; setSingleLine(true)
    }
    private fun button(s:String,action:()->Unit) = Button(this).apply {
        text=s; setTextColor(navy); setBackgroundColor(teal); setOnClickListener { action() }
        layoutParams=LinearLayout.LayoutParams(-1,ViewGroup.LayoutParams.WRAP_CONTENT)
    }
    private fun endpoint(path:String):String {
        val base=api.text.toString().trim().trimEnd('/')
        require(base.startsWith("https://")) { "Use an HTTPS backend URL" }
        return base+path
    }
    private fun request(path:String,body:String?=null):JSONObject {
        val c=URL(endpoint(path)).openConnection() as HttpURLConnection
        c.requestMethod=if(body==null) "GET" else "POST"
        c.connectTimeout=10000; c.readTimeout=260000
        c.setRequestProperty("Accept","application/json")
        if(body!=null) {
            c.doOutput=true; c.setRequestProperty("Content-Type","application/json")
            c.outputStream.use { it.write(body.toByteArray(Charsets.UTF_8)) }
        }
        val code=c.responseCode
        val stream=if(code in 200..299) c.inputStream else c.errorStream
        val data=stream?.bufferedReader()?.use { it.readText() } ?: "{}"
        c.disconnect()
        if(code !in 200..299) error("Backend HTTP $code: $data")
        return JSONObject(data)
    }
    private fun checkHealth() {
        status.text="Checking backend…"
        thread {
            try {
                val d=request("/health")
                runOnUiThread {
                    val ready=d.optBoolean("analysis_ready",false)
                    status.text=if(ready) "API reachable • analysis configured" else "API reachable • analysis NOT ready"
                    status.setTextColor(if(ready) teal else Color.YELLOW)
                }
            } catch(e:Exception) {
                runOnUiThread { status.text="Backend error: ${e.message}"; status.setTextColor(Color.RED) }
            }
        }
    }
    private fun runAnalysis() {
        val symbol=ticker.text.toString().trim()
        if(!symbol.matches(Regex("[A-Za-z0-9.^=-]{1,20}"))) { result.text="Enter a valid ticker"; return }
        result.text="Research running…"
        thread {
            try {
                val d=request("/v1/analyze",JSONObject().put("ticker",symbol).toString())
                val report=d.optString("report","")
                runOnUiThread {
                    result.text="Status: ${d.optString("status")}\nTicker: ${d.optString("ticker")}\n\n${d.optString("summary")}\n\n${report.ifBlank { "No report available. Configure the backend first." }}"
                }
            } catch(e:Exception) {
                runOnUiThread { result.text="Analysis unavailable\n${e.message}\n\nNo signal generated." }
            }
        }
    }
}
