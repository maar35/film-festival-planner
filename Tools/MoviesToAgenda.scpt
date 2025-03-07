property festival : "MTMF"
property edition : "2025"
property initialMinDate : date "dinsdag 31 december 2199 om 00:00:00"
property initialMaxDate : date "zondag 31 december 1899 om 00:00:00"
property maartenInfo : {cal:"Film", eventsAdded:0, minDate:initialMinDate, maxDate:initialMaxDate}
property adrienneInfo : {cal:"IFFR Adrienne", eventsAdded:0, minDate:initialMinDate, maxDate:initialMaxDate}
property manfredInfo : {cal:"IFFR Manfred", eventsAdded:0, minDate:initialMinDate, maxDate:initialMaxDate}
property calendarInfoList : {maartenInfo}

repeat with calendarInfo in calendarInfoList
	set the eventsAdded of calendarInfo to 0
end repeat

property posixFile : "/Users/maartenroos/Documents/Film/" & festival & "/" & festival & edition & "/FestivalPlan/calendar.csv"
set fp to (open for access (POSIX file posixFile))

set err to 0
set skipHeader to true
repeat while err = 0
	try
		set screeningRecord to read fp as «class utf8» using delimiter ";" until linefeed
		if skipHeader then
			set skipHeader to false
		else
			my create_calendar_events(the screeningRecord)
		end if
	on error the error_message number the error_number
		set err to 1
		if error_number is not -39 then
			display dialog "Error: " & the error_number & ". " & the error_message buttons {"OK"} default button 1
		end if
	end try
end repeat
close access fp

on create_calendar_events(screeningRecord)
	repeat with calendarInfo in calendarInfoList
		my create_one_event(screeningRecord, calendarInfo)
		set the eventsAdded of calendarInfo to (the eventsAdded of calendarInfo) + 1
	end repeat
end create_calendar_events

on create_one_event(screeningRecord, calendarInfo)
	set theTitle to item 1 of screeningRecord
	set theLocation to item 2 of screeningRecord
	set theStartDate to (date (item 3 of screeningRecord))
	set theEndDate to (date (item 4 of screeningRecord))
	set theUrl to item 5 of screeningRecord
	set theNotes to item 6 of screeningRecord
	set theDesc to my replace(theNotes, "|", return)
	tell application "Calendar"
		tell calendar the (cal of calendarInfo)
			try
				set newEvent to make new event with properties {summary:theTitle, location:theLocation, start date:theStartDate, end date:theEndDate, url:theUrl, description:theDesc}

				tell newEvent to make new display alarm at end of display alarms with properties {trigger interval:-15}
			on error errMsg number errNum
				-- do nothing, ignore error as the script seems to work and sets alarm
			end try
			view calendar at theStartDate
		end tell
	end tell
	if the theStartDate is less than the minDate of calendarInfo then
		set the minDate of calendarInfo to theStartDate
	end if
	if the theEndDate is greater than the maxDate of calendarInfo then
		set the maxDate of calendarInfo to theEndDate
	end if
end create_one_event

on replace(input, x, y)
	set text item delimiters to x
	set textItems to text items of input
	set text item delimiters to y
	textItems as text
end replace

tell me to activate

repeat with calendarInfo in calendarInfoList
	set theCalendar to the cal of calendarInfo
	set nrAdded to the eventsAdded of calendarInfo
	set theMinDate to the minDate of calendarInfo
	set theMaxDate to the maxDate of calendarInfo
	set theDialogText to (nrAdded as string) & " events added to calendar " & theCalendar & return & return & "from " & theMinDate & return & "to " & theMaxDate & "."
	display dialog theDialogText buttons {"OK"} default button 1
end repeat


