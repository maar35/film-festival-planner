property maartenColumn : 3
property adrienneColumn : 4
property manfredColumn : 5
property earlyPast : (current date) - 1000 * days
property lateFuture : (current date) + 1000 * days
property maartenInfo : {cal:"Film", textitem:maartenColumn, eventsAdded:0, minDate:lateFuture, maxDate:earlyPast, messageText:""}
property adrienneInfo : {cal:"IFFR Adrienne", textitem:adrienneColumn, eventsAdded:0, minDate:lateFuture, maxDate:earlyPast, messageText:""}
property manfredInfo : {cal:"IFFR Manfred", textitem:manfredColumn, eventsAdded:0, minDate:lateFuture, maxDate:earlyPast, messageText:""}
property calendarInfoList : {maartenInfo}

repeat with calendarInfo in calendarInfoList
	set the eventsAdded of calendarInfo to 0
	set the messageText of calendarInfo to ""
end repeat

set fp to (open for access (POSIX file "/Users/maartenroos/Documents/Film/IDFA/IDFA2020/CalendarFood.csv"))

set err to 0
set skipHeader to true
repeat while err = 0
	try
		set screeningRecord to read fp using delimiter ";" until linefeed
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
		set texItemNr to the textitem of calendarInfo
		set tickInfo to item texItemNr of screeningRecord
		if tickInfo is equal to "WAAR" then
			my create_one_event(screeningRecord, calendarInfo, tickInfo)
			set the eventsAdded of calendarInfo to (the eventsAdded of calendarInfo) + 1
		end if
	end repeat
end create_calendar_events

on create_one_event(screeningRecord, calendarInfo, tickInfo)
	--set theTicketStatus to item 3 of screeningRecord
	set theStartYMD to item 2 of screeningRecord
	set theStartD to text 9 through 10 of theStartYMD
	set theStartM to text 6 through 7 of theStartYMD
	set theStartY to text 1 through 4 of theStartYMD
	set theStartDMY to theStartD & "-" & theStartM & "-" & theStartY
	set theStartHHMM to item 9 of screeningRecord
	set theEndHHMM to item 10 of screeningRecord
	set theStartDate to (date (theStartDMY & " " & theStartHHMM))
	if theEndHHMM is greater than theStartHHMM then
		set theEndDate to (date (theStartDMY & " " & theEndHHMM))
	else
		set theEndDate to ((date (theStartDMY & " " & theEndHHMM)) + 1 * days)
	end if
	set theLocation to item 8 of screeningRecord
	set theTitle to item 11 of screeningRecord
	set theNumberOfFilms to (item 12 of screeningRecord) as number
	set theExtra to item 13 of screeningRecord
	set theQandA to item 14 of screeningRecord
	set theUrl to item 15 of screeningRecord
	set theDesc to item 16 of screeningRecord
	if theNumberOfFilms is equal to 2 then
		set theDesc to theExtra & return & theDesc
	else if theNumberOfFilms is greater than 2 then
		set theDesc to "Voorstelling heeft " & theNumberOfFilms & " onderdelen" & return & theDesc
	end if
	if theQandA is equal to "WAAR" then
		set theDesc to "Q&A" & return & theDesc
	end if
	tell application "Calendar"
		tell calendar the (cal of calendarInfo)
			try
				set newEvent to make new event with properties {summary:theTitle, location:theLocation, start date:theStartDate, end date:theEndDate, url:theUrl, description:theDesc}

				tell newEvent to make new display alarm at end of display alarms with properties {trigger interval:-30}
			on error errMsg number errNum
				-- do nothing, ignore error as the script seems to work and creates appointment
				set the messageText of calendarInfo to (the messageText of calendarInfo) & return & errNum & return & errMsg
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

tell me to activate

repeat with calendarInfo in calendarInfoList
	set theCalendar to the cal of calendarInfo
	set nrAdded to the eventsAdded of calendarInfo
	set theMinDate to the minDate of calendarInfo
	set theMaxDate to the maxDate of calendarInfo
	set theErrMessage to the messageText of calendarInfo
	set dlog_text to (nrAdded as string) & " events added to calendar " & theCalendar & return & return & "from " & theMinDate & return & "to " & theMaxDate & "." & return & return & theErrMessage
	display dialog dlog_text buttons {"OK"} default button 1
end repeat


