# Perspective-Powered-Personalized-News-Aggregator-A-Multi-dimensional-Framework-Content-Analysis-
Multi-dimensional news analysis framework featuring RSS aggregation, psycholinguistic manipulation detection, misinformation scoring, cognitive accessibility adaptations, and advanced sentiment insights with TTS support.
## ✨ Features

### 🔍 **Advanced Analysis**
- **Psycholinguistic Manipulation Detection** - Identifies fear appeals, authority appeals, bandwagon effects, scarcity tactics, and more
- **Misinformation Risk Assessment** - Fact-checking with source credibility analysis
- **News DNA Analysis** - Content fingerprinting and similarity detection
- **Sentiment Analysis** - Real-time emotional tone assessment

### 🧠 **Neurodiversity Support**
- **ADHD-Optimized Display** - Focus mode with progress indicators and section breaks
- **Autism-Friendly Format** - Structured, predictable layouts with clear numbering
- **Dyslexia Support** - Syllable breaks, shorter sentences, and readable fonts
- **Accessibility Controls** - Font size, line spacing, high contrast mode

### 📰 **Smart Aggregation**
- **Multi-Source RSS Feeds** - CNN, BBC, The Guardian, and custom sources
- **Interest-Based Filtering** - Personalized content based on user preferences
- **Behavioral Learning** - Recommendations improve with usage
- **Duplicate Detection** - Intelligent deduplication across sources

### 🎯 **User Experience**
- **Reader Mode** - Distraction-free full article reading
- **Text-to-Speech** - Audio playback for accessibility
- **Interactive Charts** - Sentiment trends and analytics
- **Reading History** - Track and revisit articles

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- SQLite3
- Internet connection for news feeds

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/kg290/perspective-powered-news-aggregator.git
cd perspective-powered-news-aggregator
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Download NLTK data**
```bash
python -c "import nltk; nltk.download('punkt')"
```

4. **Run the application**
```bash
python main.py
```

## 📱 Usage

### First Launch
1. Set up your interests (comma-separated): `technology, health, politics`
2. The app will fetch articles from default sources
3. Explore different tabs for various features

### Accessibility Setup
1. Navigate to the **🔧 Accessibility** tab
2. Select your cognitive profile (Standard, ADHD, Autism, Dyslexia)
3. Adjust font size and visual preferences
4. Test voice features and apply settings

### Advanced Features
- **Manipulation Analysis**: View psychological manipulation scores
- **Fact Check**: See misinformation risk assessments
- **News DNA**: Explore article similarities and patterns
- **Sentiment Insights**: Analyze emotional trends in your reading

## 🏗️ Architecture

```
main.py                          # Main application entry point
├── NewsApp                      # Primary GUI application class
├── PsycholinguisticAnalyzer     # Manipulation detection engine
├── MisinformationDetector       # Fact-checking and credibility assessment
├── NeurodiversityAdapter        # Accessibility content adaptation
├── NewsDNAAnalyzer             # Content fingerprinting and similarity
└── ReaderModeWindow            # Enhanced reading interface
```

### Databases
- `manipulation_analysis.db` - Stores manipulation scores
- `news_dna.db` - Content fingerprints and similarity data
- `user_profile.json` - User preferences and interests
- `click_log.json` - Reading history and behavior

## 🔧 Configuration

### RSS Sources
Edit sources in the Settings tab or modify `DEFAULT_RSS_SOURCES` in the code:
```python
DEFAULT_RSS_SOURCES = [
    "https://rss.cnn.com/rss/edition.rss",
    "https://feeds.bbci.co.uk/news/rss.xml",
    "https://www.theguardian.com/world/rss"
]
```

### API Keys (Optional)
For enhanced features, add API keys:
```python
GNEWS_API_KEY = "your_gnews_api_key"
REALTIME_NEWS_API_KEY = "your_realtime_news_api_key"
```

### Accessibility Profiles
Customize cognitive profiles in `accessibility_settings.json`:
```json
{
    "cognitive_profile": "adhd",
    "font_size": 14,
    "line_spacing": 1.5,
    "high_contrast": true,
    "auto_read": false
}
```

## 🧪 Testing

### Sample Data
The application includes sample articles for testing when external feeds are unavailable.

### Voice Testing
Use the "🔊 Test Voice" button in accessibility settings to verify text-to-speech functionality.

### Manipulation Detection Testing
Try these sample phrases to see manipulation detection:
- "BREAKING: Crisis situation requires immediate action!"
- "Experts say this will change everything"
- "Join millions who are already taking action"

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow PEP 8 style guidelines
- Add docstrings for new functions
- Test accessibility features with different profiles
- Ensure database operations are properly handled

## 📊 Advanced Features

### Manipulation Patterns Detected
- **Fear Appeals**: Crisis, disaster, emergency language
- **Authority Appeals**: Expert endorsements, official sources
- **Bandwagon Effects**: Popularity and trending appeals
- **Scarcity Tactics**: Limited time, exclusive offers
- **Confirmation Bias**: "As predicted" language
- **False Dichotomy**: Either/or forced choices

### Accessibility Adaptations
- **ADHD**: Progress indicators, section breaks, keyword highlighting
- **Autism**: Structured format, predictable layouts, content tables
- **Dyslexia**: Syllable breaks, shorter sentences, dyslexia-friendly fonts

## 🛠️ Troubleshooting

### Common Issues

**"No articles found"**
- Check internet connection
- Verify RSS feed URLs are accessible
- Try refreshing articles manually

**Voice not working**
- Ensure `pyttsx3` is properly installed
- Check system audio settings
- Try different voice engines

**Database errors**
- Delete `.db` files to reset databases
- Check file permissions
- Ensure SQLite3 is available

### Performance Tips
- Limit article processing to 200 articles for better performance
- Clear reading history periodically
- Use sample data for testing without internet

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **feedparser** - RSS feed parsing
- **BeautifulSoup** - HTML content processing
- **TextBlob** - Natural language processing
- **NLTK** - Advanced text analysis
- **pyttsx3** - Text-to-speech functionality
- **tkinter** - GUI framework
- **matplotlib** - Data visualization

## 📞 Support

For support, please open an issue on GitHub or contact the maintainer.

---

**Built with ❤️ for accessible, intelligent news consumption**
