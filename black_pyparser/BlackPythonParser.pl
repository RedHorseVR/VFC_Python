#use
	
	use File::stat qw(stat);
	
sub LoadFileAsString {
	local ( $file ) = @_;
	local ( $keyfile ) ;
	open( FILE, $file );
	while(<FILE>) {
		s/^ *\n//;
		tr/\t/ /;
		$keyfile = "$keyfile$_";
		}
	
	close ( FILE );
	$keyfile; }
# main
	$cmd_line = $ENV{'QUERY_STRING'} ;
	
	($cmd_line) = @ARGV;
	
	$outputVFC =  "$cmd_line.vfc" ;
	$file = $cmd_line ;
	print( STDOUT  "parse file =  $cmd_line  ...  \n" );
	$lasttime = 0;
	$I = 2;
	Parse();
	while( $I < 1 ) {
		$I = $I+1;
		$nowtime = stat($file)->mtime;
		
		
		if ( $nowtime != $lasttime )
		{
			Parse();
			$lasttime = stat($file)->mtime;
			print( STDOUT  "\nlistening and autoparse for file =  $cmd_line  ...  \n" );
		}else{
			}
		
		select(undef, undef, undef, 0.25);
		}
	
	print "done\n";
	
sub NumTabs{ local ( $inputSTR ) = @_;
	local($match) = @_;
	
	$match= tr/^\t*/^\t*/;
	return  $match ;
}
sub PrintTabs{ local ( $num ) = @_;
	local( $i ) = 0;
	while(  $i  < $num ) {
		print( "\t|" );
		$i=$i+1;}
	
	}
my @stack;
sub PrintStack{
	
	
	print "";
	PrintTabs(10);
	print "-------- STACK:-------\n";
	foreach $val (@stack){
		$val =~ s/\t*//g;
		$val =~ s/^ +//g;
		PrintTabs(10);
		print( "$val\n" );
		}
	
	PrintTabs(10);
	print "^----------------^\n";
	}
sub Flow{ local ( $lastCode ) = @_;
	$LOOP = "^\t*(for|while|do)";
	$BRANCH = "^\t*(if|try)";
	$WITH = "^\t*(with)";
	$PEND = "^\t*(else|except)";
	$END = "^\t*(break|continue|return)";
	$OUTPUT = "^\t*(print)";
	$INPUTOBJ = "^\t*(class)";
	$INPUT = "^\t*(def|class)";
	$EVENT = "^(import|from)";
	$PATH = "^\t*(else|elif)";
	$Flow = (     $lastCode =~m/$INPUT/     ||   $lastCode =~m/$LOOP/     ||   $lastCode =~m/$BRANCH/    ||  $lastCode =~ m/$EVENT/ )  ;
	return 1; }
sub getCode { local ( $code ) = @_;
	$code =~ s/    /\t/g ;
	$code =~ s/#.*$//;
	return $code ; }
sub getComment { local ( $comment ) = @_;
	if ( $comment =~ m/^.*#{1}/  )
	{
		$comment =~ s/^.*#{1}//;
	}else{
		$comment ="" ;
		}
	return $comment; }
sub getIndents { local ( $Line ) = @_;
	$count =  NumTabs( $Line  ) ;
	return $count; }
sub getMultiline { local ($multiLine,  $Line ) = @_;
	if ( $multiLine==0 && ( $Line =~ m/^\t*\"\"\"/   ||    $Line =~ m/^\t*\'\'\'/ )  )
	{
		$multiLine = 1;
		print( "set(#);\/\/$_ CONVERTED MULTILINE COMMENTS TO SINGLES\n" );
		return 1;
	} else {
		if (    $multiLine==1 && ( $Line =~m/^\t*\"\"\"/   || $Line =~m/^\t*\'\'\'/)   )
		{
			$multiLine = 0;
			return 0;
			}
		}
	return $multiLine ; }
sub Parse{
	open OUTFILE,  ">" ,   $outputVFC  or die "Cannot open output: $!";
	open( FILE, $cmd_line );
	print( "...parseing $cmd_line\n" );
	$lastCount = 0;
	$ParsedFile  = "";
	$multiLine = 0;
	$LINE = 0;
	while(<FILE>) {
		$_ =~ s/    /\t/g ;
		$_ =~ s/\n// ;
		$multiLine = getMultiline( $multiLine,  $_ ) ;
		if ( $multiLine==1  )
		{
			if (   $multiLine == 1  )
			{
				print( "set(#);\/\/$_\n" );
				}
		}else{
			$LEVEL = getIndents( $_  ) ;
			$COMM = getComment( $_ ) ;
			$CODE = getCode( $_ ) ;
			$CODE =~ s/^\t*// ;
			$LINE = $LINE + 1 ;
			
			if (    $CODE =~ m/^$/   )
			{
				$LEVEL = $lastCount ;
				$COMM = "--EMPTY---------";
			} else {
				if (  $CODE =~  /^(from|import)/  )
				{
					print "event($CODE);\/\/-------------event  $COMM\n";
					
				} else {
					if (  $CODE =~ m/^(else|elif)/  )
					{
						$LEVEL = $lastCount ;
						print "path($CODE);\/\/-------------path $COMM\n";
					} else {
						if ( $CODE =~ m/$INPUT/  ||  $CODE =~ m/$BRANCH/    )
						{
						}else{
							print "set($CODE);\/\/$COMM\n";
							}
						}
					}
				}
			
			if (  $CODE=~  m/^[\t ]*\):/   || $CODE=~  m/^[\t ]*\)/    || $CODE=~  m/^[\t ]*\]/   || $CODE=~  m/^[\t ]*\[/   )
			{
				$LEVEL = $lastCount ;
				$COMM  = "$COMM ------------------------- ADDED TAB";
				}
			$change =  $LEVEL  -  $lastCount  ;
			
			if ( $change > 0 )
			{
				
				if ( Flow( $lastCode ) )
				{
					
					$st = substr( $lastCode, 0, 10 );
					push( @stack,$st );
					
					if ( $st =~ m/$INPUT/ )
					{
						
						print "input($lastCode);\/\/$COMM\n";
						print "branch();\/\/\n";
						print "path();\/\/\n";
					}else{
						if ( $st =~ m/$BRANCH/ )
						{
							print "branch( $lastCode );\/\/$COMMt\n";
						}else{
							print "process($lastCode);\/\/$COMM\n";
							}
						}
					
					}
				
			}else{
				if ( $change <  0 )
				{
					$idx = $change ;
					
					while( $idx < 0 ) {
						$stack_value = pop( @stack );
						$st = substr( $stack_value, 0, 12 );
						$idx = $idx + 1 ;
						
						if ( $st =~ m/$INPUT/ )
						{
							print "path();\/\/\n";
							print "bend();\/\/$st--- pop \n";
							print "end();\/\/$st\n";
						}else{
							
							}
						if ( $st =~ m/$BRANCH/ )
						{
							print "bend();\/\/$st --- pop\n";
						}else{
							
							}
						}
					
				}else{
					}
				}
			
			$lastCount = $LEVEL;
			
			$lastComment = $COMM;
			$lastCode = $CODE;
			}
		}
	
	close ( FILE );
	
	
	close ( OUTFILE );
	
	
	
	}
sub printFooter{
	$rootfile = $file;
	$rootfile =~ s/^.*\\//;
	print( OUTFILE  ";INSECT" );
	print( OUTFILE  "A EMBEDDED SESSION INFORMATION\n" );
	print( OUTFILE  "; 255 16777215 65280 16777088 16711680 255 8388608 0 255 255 65535 65280 4210688 \n");
	print( OUTFILE  "$rootfile.py   #\"\"\"  #\"\"\"  \n");
	print( OUTFILE  "; notepad++.exe \n");
	print( OUTFILE  ";INSECT" );
	print( OUTFILE  "A EMBEDDED ALTSESSION INFORMATION\n");
	print( OUTFILE  "; 262 123 765 1694 0 170   379   4294966903    python.key  0");
	}
#  Export  Date: 08:50:26 PM - 26:Apr:2023.

