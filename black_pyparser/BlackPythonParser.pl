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
sub Flow{ local ( $lastCode ) = @_;
	$LOOP = "^\t*(for|while|do)";
	$BRANCH = "^\t*(if|try)";
	$WITH = "^\t*(with)";
	$PATH = "^\t*(else|elif)";
	$PEND = "^\t*(else|except)";
	$END = "^\t*(break|continue|return)";
	$OUTPUT = "^\t*(print)";
	$INPUTOBJ = "^\t*(class)";
	$INPUT = "^\t*(def|class)";
	$EVENT = "^\t*(import)";
	$Flow = (     $lastCode =~m/$INPUT/     ||   $lastCode =~m/$LOOP/     ||   $lastCode =~m/$BRANCH/    ||  $lastCode =~ m/$EVENT/ )  ;
	return $Flow; }
sub Parse{
	open OUTFILE,  ">" ,   $outputVFC  or die "Cannot open output: $!";
	open( FILE, $cmd_line );
	print( "...parseing $cmd_line\n" );
	my @stack;
	$lastCount = 0;
	$ParsedFile  = "";
	while(<FILE>) {
		$_ =~ s/    /\t/g ;
		$comment = "$_";
		if ( $_ =~ m/^\n/  )
		{
		}else{
			$_ =~ s/\n// ;
			$T =$_;
			$count =  NumTabs( $_ ) ;
			
			$change = -$lastCount + $count ;
			$comment = "$_";
			
			if ( $change > 0 )
			{
				if ( Flow( $lastCode ) )
				{
					
					push( @stack,"$lastCode" );
					}
			}else{
				if ( $change <  0 )
				{
					
					
					$idx = $change ;
					while( $idx < 0 ) {
						$stack_value = pop( @stack );
						if ( Flow( $stack_value )  )
						{
							$comment_flow =  "\n#--------------------------------- $stack_value"  ;
							
						}else{
							}
						$idx = $idx + 1 ;
						}
					
				}else{
					
					}
				}
			
			$code = "$_";
			
			
			s/#.*$//;
			if ( $comment =~ s/^.*#{1}//  )
			{
				if ( $comment =~ m/^end/ )
				{
					$line ="end($_);\//$comment";
				}else{
					$line ="set($_);\//$comment";
					}
			} else {
				$comment = "";
				}
			print( "$_" );
			$comment = "$comment_flow$comment";
			$comment_flow =  "" ;
			if ( $comment ne '' )
			{
				print( "\t #  $comment \n" );
			} else {
				print( "\n" );
				}
			$line ="set($_);\//$comment";
			
			
						if(   m/$INPUTOBJ/  )  {
				$line ="input($_);\//$comment";
				$ParsedFile  = "$ParsedFile$line\n";
				$line ="branch();";
			
				
			} if(   m/$INPUT/  )  {
				$line ="input($_);\//$comment";
				
			} if(   m/$EVENT/  )  {
				$line ="event($_);\//$comment";
			} if(   m/$OUTPUT/  )  {
				$line ="output($_);\//$comment";
			} if(   m/$LOOP/  )  {
				$line ="loop($_);\//$comment";
				
			} if(   m/$WITH/  )  {
				$line ="branch($_);\//$comment";
			
				$ParsedFile  = "$ParsedFile$line\n";
				$line ="path();";
				
			} if(   m/$BRANCH/  )  {
				$line ="branch($_);\//$comment";
			
				$ParsedFile  = "$ParsedFile$line\n";
				$line ="path();";
				
			} if(   m/$PATH/  )  {
				$line ="path($_);\//$comment";
				
			} if(   m/$PEND/  )  {
				$stack_value = pop( @stack );
				if ( $stack_value =~ "bend" )
				{
					
					
				}else{
					
					}
				$line ="path($_);\//$comment";
				
			} if(   m/$END/  )  {
				$line ="end($_);\//$comment";
				}
			$ParsedFile  = "$ParsedFile$line\n";
			$line = "";
			$lastCount = $count ;
			$lastChange = $change ;
			$lastComment = $comment ;
			$lastCode = $code  ;
			}
		}
	
	close ( FILE );
	
	$stack_value = pop( @stack );
	while( $stack_value  ) {
		$line ="$stack_value();";
		$ParsedFile  = "$ParsedFile$line\n";
		$stack_value = pop( @stack );
		}
	
	
	print( OUTFILE $ParsedFile );
	printFooter( );
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
#  Export  Date: 01:30:16 AM - 25:Apr:2023.

