using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net;
using System.Text;
using System.Text.RegularExpressions;
using System.Xml.Linq;

namespace PresentScreenings.TableView
{
    public static class WebUtility
    {
        #region Public Members
        public enum MediumCatagory
        {
            Films,
            CombinedProgrammes,
            Events
        }

        public enum ParseInfoType
        {
            Description,
            Article,
            ScreenedFilms
        }
        #endregion

        #region Private Variables
        struct ParseInfo
        {
            public ParseInfoType type;
            public string description;
            public Regex re;
            public Regex filterRe;
            public string filterReplacement;
        }
        static Dictionary<MediumCatagory, List<ParseInfo>> _parseInfoByCatagory;
        #endregion

        #region Properties
        static public Dictionary<MediumCatagory, string> FolderByCatagory;
        #endregion

        #region Constructors
        static WebUtility()
        {
            FolderByCatagory = new Dictionary<MediumCatagory, string> { };
            FolderByCatagory[MediumCatagory.Films] = "films";
            FolderByCatagory[MediumCatagory.CombinedProgrammes] = "verzamelprogrammas";
            FolderByCatagory[MediumCatagory.Events] = "events";
            var descriptionParseInfo = new ParseInfo
            {
                type = ParseInfoType.Description,
                description = "Description",
                re = new Regex(@"\<meta name=""description"" content=""(.*)"" />")
            };
            var articleParseInfo = new ParseInfo
            {
                type = ParseInfoType.Article,
                description = "Article",
                //articelParseInfo.re = new Regex(@"\<article.*?(\<p\>.*\</p\>).*\</article\>", RegexOptions.Singleline);
                re = new Regex(@"\<article.*?(\<p\>.*\</p\>)\s*\</div\>\s*\</article\>", RegexOptions.Singleline)
            };
            var screenedFilmsParseInfo = new ParseInfo
            {
                type = ParseInfoType.ScreenedFilms,
                description = "Screened films",
                re = new Regex(@"\<section class=""rectangle-column""\>\s*\<h2\>(.*?)\</h2\>\s*\<span class=""hover-info""\>.*?\<p class=""full-text""\>(.*?)\</p\>", RegexOptions.Singleline),
                filterRe = new Regex(@"^(.*)(\<main.*\</main\>)(.*)$", RegexOptions.Singleline),
                filterReplacement = @"$2"
            };
            _parseInfoByCatagory = new Dictionary<MediumCatagory, List<ParseInfo>> { };
            _parseInfoByCatagory[MediumCatagory.Films] = new List<ParseInfo> { descriptionParseInfo, articleParseInfo };
            _parseInfoByCatagory[MediumCatagory.Events] = new List<ParseInfo> { articleParseInfo };
            _parseInfoByCatagory[MediumCatagory.CombinedProgrammes] = new List<ParseInfo> { articleParseInfo, screenedFilmsParseInfo };
        }
        #endregion

        #region Private Methods
        #endregion

        #region Public Methods

        /// <summary>
        /// Htmls to plain text.
        /// By Ben Anderson (https://stackoverflow.com/questions/286813/how-do-you-convert-html-to-plain-text)
        /// </summary>
        /// <returns>The plain text.</returns>
        /// <param name="html">Html.</param>
        public static string HtmlToPlainText(string html)
        {
            const string tagWhiteSpace = @"(>|$)(\W|\n|\r)+<";//matches one or more (white space or line breaks) between '>' and '<'
            const string stripFormatting = @"<[^>]*(>|$)";//match any character between '<' and '>', even when end tag is missing
            const string lineBreak = @"<(br|BR)\s{0,1}\/{0,1}>";//matches: <br>,<br/>,<br />,<BR>,<BR/>,<BR />
            var lineBreakRegex = new Regex(lineBreak, RegexOptions.Multiline);
            var stripFormattingRegex = new Regex(stripFormatting, RegexOptions.Multiline);
            var tagWhiteSpaceRegex = new Regex(tagWhiteSpace, RegexOptions.Multiline);

            var text = html;
            //Decode html specific characters
            text = System.Net.WebUtility.HtmlDecode(text);
            //Remove tag whitespace/line breaks
            text = tagWhiteSpaceRegex.Replace(text, "><");
            //Replace <br /> with line breaks
            text = lineBreakRegex.Replace(text, Environment.NewLine);
            //Strip formatting
            text = stripFormattingRegex.Replace(text, string.Empty);

            return text;
        }

        public static string UrlString(string title, MediumCatagory catagory)
        {
            string baseUrl = "https://iffr.com/nl/" + ScreeningsPlan.FestivalYear + "/" + FolderByCatagory[catagory] + "/";
            var quotes = @"['`""]";
            var disposables = @"[./()?]";
            var strippables = @"(" + quotes + @"+\s*)|" + disposables + @"+";
            var reStrip = new Regex(strippables, RegexOptions.CultureInvariant);
            var strippedTitle = reStrip.Replace(title.ToLowerInvariant(), "");
            var extraWordChars = @"[–★]";
            var nonWords = @"[\W-" + extraWordChars + "]+";
            var reReplace = new Regex(nonWords, RegexOptions.CultureInvariant); // space or connector punctuation.
            var result = baseUrl + reReplace.Replace(strippedTitle, "-");
            return result;
        }

        public static FilmInfo TryParseUrlSummary(HttpWebRequest request, string url, MediumCatagory catagory, int filmId)
        {
            var response = request.GetResponse() as HttpWebResponse;
            var stream = new StreamReader(response.GetResponseStream());
            var text = stream.ReadToEnd();
            stream.Close();
            var builder = new StringBuilder();
            var allParsesFailed = false;
            var filmDescription = string.Empty;
            var article = string.Empty;
            var ScreenedFileDescriptionByTitle = new Dictionary<string, string> { };
            foreach (var parseInfo in _parseInfoByCatagory[catagory])
            {
                var success = false;
                if (parseInfo.filterRe != null && parseInfo.filterReplacement != null)
                {
                    text = parseInfo.filterRe.Replace(text, parseInfo.filterReplacement);
                }
                foreach (Match match in parseInfo.re.Matches(text))
                {
                    //builder.AppendFormat($"-match-at-{match.Index}-->\n");
                    var groupCount = match.Groups.Count;
                    string screenedFilmTitle = string.Empty;
                    for (int groupNumber = 1; groupNumber < groupCount; groupNumber++)
                    {
                        //builder.AppendFormat($"-group-{groupNumber}-->\n");
                        var textUnit = match.Groups[groupNumber].Value;
                        switch (parseInfo.type)
                        {
                            case ParseInfoType.Description:
                                filmDescription = textUnit;
                                break;
                            case ParseInfoType.Article:
                                article = textUnit;
                                break;
                            case ParseInfoType.ScreenedFilms:
                                if (groupNumber % 2 == 1)
                                {
                                    screenedFilmTitle = textUnit;
                                }
                                else
                                {
                                    ScreenedFileDescriptionByTitle[screenedFilmTitle] = textUnit;
                                }
                                break;
                        }
                    }
                    success = true;
                }
                if (!success)
                {
                    allParsesFailed = true;
                }
            }
            if (allParsesFailed)
            {
                builder.AppendLine($"URL {url} could not be parsed.");
                builder.AppendLine("===");
                builder.Append(text);
                throw new UnparseblePageException(builder.ToString());
            }
            var info = new FilmInfo(filmId, catagory, url, filmDescription, article);
            foreach (string title in ScreenedFileDescriptionByTitle.Keys)
            {
                info.AddScreenedFilm(title, ScreenedFileDescriptionByTitle[title]);
            }
            return info;
        }

        public static void SaveFilmInfoAsXml(List<FilmInfo> filmInfos, string path)
        {
            var xml = new XElement
            (
                "FilmInfos",
                from filmInfo in filmInfos
                select new XElement
                (
                    "FilmInfo",
                    new XAttribute("FilmId", filmInfo.FilmId),
                    new XAttribute("MediumCatagory", filmInfo.MediumCatagory),
                    new XAttribute("Url", filmInfo.Url),
                    new XAttribute("FilmDescription", filmInfo.FilmDescription),
                    new XAttribute("FilmArticle", filmInfo.FilmArticle),
                    new XElement
                    (
                        "ScreenedFilms",
                        from screenedFilm in filmInfo.ScreenedFilms
                        select new XElement
                        (
                            "ScreenedFilm",
                            new XAttribute("Title", screenedFilm.Title),
                            new XAttribute("Description", screenedFilm.Description)
                        )
                    )
                )
            );
            xml.Save(path);
        }

        public static List<FilmInfo> LoadFilmInfoFromXml(string path)
        {
            var filmInfos = new List<FilmInfo> { };
            XElement root;
            try
            {
                root = XElement.Load(path);
            }
            catch (FileNotFoundException)
            {
                return filmInfos;
            }
            catch(System.Exception)
            {
                return filmInfos;
            }
            var filmInfoElements =
                from el in root.Elements("FilmInfo")
                select
                (
                    (int)el.Attribute("FilmId"),
                    (string)el.Attribute("MediumCatagory"),
                    (string)el.Attribute("Url"),
                    (string)el.Attribute("FilmDescription"),
                    (string)el.Attribute("FilmArticle"),
                    from s in el.Element("ScreenedFilms").Elements("ScreenedFilm")
                    select
                    (
                        (string)s.Attribute("Title"),
                        (string)s.Attribute("Description")
                    )
                );
            foreach (var filmInfoElement in filmInfoElements)
            {
                var filmInfo = new FilmInfo
                (
                    filmInfoElement.Item1,
                    StringToMediumCatagory(filmInfoElement.Item2),
                    filmInfoElement.Item3,
                    filmInfoElement.Item4,
                    filmInfoElement.Item5
                );
                foreach (var screenedFilmAttribute in filmInfoElement.Item6)
                {
                    var title = screenedFilmAttribute.Item1;
                    var description = screenedFilmAttribute.Item2;
                    filmInfo.AddScreenedFilm(title, description);
                }
                filmInfos.Add(filmInfo);
            }
            return filmInfos;
        }

        private static MediumCatagory StringToMediumCatagory(string name)
        {
            try
            {
                return (MediumCatagory)Enum.Parse(typeof(MediumCatagory), name);
            }
            catch
            {
                throw new IllegalMediumCatagoryException($"'{name}' is not a valid WebUtitlity.MediumCatagory");
            }
        }
        #endregion
    }

    public sealed class UnparseblePageException : Exception
    {
        public UnparseblePageException(string message) : base(message)
        {
        }
    }

    public sealed class IllegalMediumCatagoryException : Exception
    {
        public IllegalMediumCatagoryException(string message) : base(message)
        {
        }
    }
}

